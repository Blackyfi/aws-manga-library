#!/bin/bash
###############################################################################
# Database Backup Script
# =======================
#
# Creates backups of DynamoDB tables
# Supports:
# - On-demand backups
# - Export to S3
# - Scheduled backups
#
# Usage: ./backup-database.sh [environment] [backup-type]
# Backup types: ondemand, export, pitr
# Example: ./backup-database.sh prod ondemand
###############################################################################

set -e  # Exit on error

# Configuration
ENVIRONMENT="${1:-dev}"
BACKUP_TYPE="${2:-ondemand}"
REGION="${AWS_REGION:-us-east-1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Load environment variables
ENV_FILE="${PROJECT_ROOT}/.env.${ENVIRONMENT}"
if [ -f "${ENV_FILE}" ]; then
    source "${ENV_FILE}"
else
    echo "Error: Environment file not found: ${ENV_FILE}"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_NAME="manga-scraper-${ENVIRONMENT}-${TIMESTAMP}"

echo "========================================="
echo "Database Backup"
echo "========================================="
echo "Environment:  ${ENVIRONMENT}"
echo "Table:        ${DYNAMODB_TABLE}"
echo "Backup Type:  ${BACKUP_TYPE}"
echo "Region:       ${REGION}"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check prerequisites
if ! command -v aws &> /dev/null; then
    error "AWS CLI is not installed"
    exit 1
fi

# Verify table exists
if ! aws dynamodb describe-table --table-name "${DYNAMODB_TABLE}" --region "${REGION}" &> /dev/null; then
    error "Table ${DYNAMODB_TABLE} not found"
    exit 1
fi

success "Table verified"

# Get table size
TABLE_SIZE=$(aws dynamodb describe-table \
    --table-name "${DYNAMODB_TABLE}" \
    --region "${REGION}" \
    --query 'Table.TableSizeBytes' \
    --output text)

TABLE_SIZE_MB=$((TABLE_SIZE / 1024 / 1024))
info "Table size: ${TABLE_SIZE_MB} MB"
echo ""

# Function for on-demand backup
create_ondemand_backup() {
    echo "Creating on-demand backup..."

    BACKUP_ARN=$(aws dynamodb create-backup \
        --table-name "${DYNAMODB_TABLE}" \
        --backup-name "${BACKUP_NAME}" \
        --region "${REGION}" \
        --query 'BackupDetails.BackupArn' \
        --output text)

    if [ -z "${BACKUP_ARN}" ]; then
        error "Failed to create backup"
        exit 1
    fi

    success "Backup created: ${BACKUP_NAME}"
    info "Backup ARN: ${BACKUP_ARN}"

    # Wait for backup to complete
    info "Waiting for backup to complete..."

    BACKUP_STATUS=""
    while [ "${BACKUP_STATUS}" != "AVAILABLE" ]; do
        sleep 5

        BACKUP_STATUS=$(aws dynamodb describe-backup \
            --backup-arn "${BACKUP_ARN}" \
            --region "${REGION}" \
            --query 'BackupDescription.BackupDetails.BackupStatus' \
            --output text 2>/dev/null || echo "CREATING")

        echo -n "."
    done
    echo ""

    BACKUP_SIZE=$(aws dynamodb describe-backup \
        --backup-arn "${BACKUP_ARN}" \
        --region "${REGION}" \
        --query 'BackupDescription.BackupDetails.BackupSizeBytes' \
        --output text)

    BACKUP_SIZE_MB=$((BACKUP_SIZE / 1024 / 1024))

    success "Backup completed successfully"
    echo ""
    echo "Backup Details:"
    echo "  Name:   ${BACKUP_NAME}"
    echo "  ARN:    ${BACKUP_ARN}"
    echo "  Size:   ${BACKUP_SIZE_MB} MB"
    echo "  Status: ${BACKUP_STATUS}"
    echo ""
}

# Function to export to S3
export_to_s3() {
    echo "Exporting table to S3..."

    if [ -z "${S3_BACKUP_BUCKET}" ]; then
        error "S3_BACKUP_BUCKET not set"
        exit 1
    fi

    # Verify S3 bucket exists
    if ! aws s3 ls "s3://${S3_BACKUP_BUCKET}" 2>/dev/null; then
        error "Backup bucket not found: ${S3_BACKUP_BUCKET}"
        exit 1
    fi

    S3_PREFIX="dynamodb-exports/${ENVIRONMENT}/${BACKUP_NAME}"

    info "Exporting to s3://${S3_BACKUP_BUCKET}/${S3_PREFIX}"

    EXPORT_ARN=$(aws dynamodb export-table-to-point-in-time \
        --table-arn "arn:aws:dynamodb:${REGION}:${AWS_ACCOUNT_ID}:table/${DYNAMODB_TABLE}" \
        --s3-bucket "${S3_BACKUP_BUCKET}" \
        --s3-prefix "${S3_PREFIX}" \
        --export-format "DYNAMODB_JSON" \
        --region "${REGION}" \
        --query 'ExportDescription.ExportArn' \
        --output text 2>&1)

    if [[ "${EXPORT_ARN}" == *"error"* ]] || [ -z "${EXPORT_ARN}" ]; then
        error "Failed to start export"
        echo "${EXPORT_ARN}"
        exit 1
    fi

    success "Export started"
    info "Export ARN: ${EXPORT_ARN}"

    # Monitor export progress
    info "Monitoring export progress..."
    EXPORT_STATUS=""
    while [ "${EXPORT_STATUS}" != "COMPLETED" ]; do
        sleep 10

        EXPORT_STATUS=$(aws dynamodb describe-export \
            --export-arn "${EXPORT_ARN}" \
            --region "${REGION}" \
            --query 'ExportDescription.ExportStatus' \
            --output text 2>/dev/null || echo "IN_PROGRESS")

        if [ "${EXPORT_STATUS}" == "FAILED" ]; then
            error "Export failed"
            exit 1
        fi

        echo -n "."
    done
    echo ""

    success "Export completed successfully"
    echo ""
    echo "Export Details:"
    echo "  Location: s3://${S3_BACKUP_BUCKET}/${S3_PREFIX}"
    echo "  ARN:      ${EXPORT_ARN}"
    echo "  Format:   DYNAMODB_JSON"
    echo ""
}

# Function to enable PITR
enable_pitr() {
    echo "Managing Point-in-Time Recovery..."

    PITR_STATUS=$(aws dynamodb describe-continuous-backups \
        --table-name "${DYNAMODB_TABLE}" \
        --region "${REGION}" \
        --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus' \
        --output text)

    info "Current PITR Status: ${PITR_STATUS}"

    if [ "${PITR_STATUS}" == "ENABLED" ]; then
        success "Point-in-Time Recovery is already enabled"

        # Get earliest restore time
        EARLIEST_RESTORE=$(aws dynamodb describe-continuous-backups \
            --table-name "${DYNAMODB_TABLE}" \
            --region "${REGION}" \
            --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription.EarliestRestorableDateTime' \
            --output text)

        LATEST_RESTORE=$(aws dynamodb describe-continuous-backups \
            --table-name "${DYNAMODB_TABLE}" \
            --region "${REGION}" \
            --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription.LatestRestorableDateTime' \
            --output text)

        echo ""
        echo "PITR Details:"
        echo "  Earliest Restorable: ${EARLIEST_RESTORE}"
        echo "  Latest Restorable:   ${LATEST_RESTORE}"
        echo ""
    else
        info "Enabling Point-in-Time Recovery..."

        aws dynamodb update-continuous-backups \
            --table-name "${DYNAMODB_TABLE}" \
            --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
            --region "${REGION}"

        success "Point-in-Time Recovery enabled"
        echo ""
    fi
}

# List existing backups
list_backups() {
    echo "Listing existing backups..."
    echo ""

    aws dynamodb list-backups \
        --table-name "${DYNAMODB_TABLE}" \
        --region "${REGION}" \
        --query 'BackupSummaries[].[BackupName,BackupCreationDateTime,BackupStatus,BackupSizeBytes]' \
        --output table

    echo ""
}

# Clean old backups
clean_old_backups() {
    echo "Cleaning old backups..."

    RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
    CUTOFF_DATE=$(date -u -d "${RETENTION_DAYS} days ago" +%Y-%m-%d 2>/dev/null || date -u -v-${RETENTION_DAYS}d +%Y-%m-%d)

    info "Removing backups older than ${RETENTION_DAYS} days (before ${CUTOFF_DATE})"

    OLD_BACKUPS=$(aws dynamodb list-backups \
        --table-name "${DYNAMODB_TABLE}" \
        --region "${REGION}" \
        --time-range-upper-bound "${CUTOFF_DATE}T00:00:00Z" \
        --query 'BackupSummaries[].BackupArn' \
        --output text)

    if [ -z "${OLD_BACKUPS}" ]; then
        info "No old backups to clean"
    else
        BACKUP_COUNT=0
        for backup_arn in ${OLD_BACKUPS}; do
            aws dynamodb delete-backup \
                --backup-arn "${backup_arn}" \
                --region "${REGION}" > /dev/null

            ((BACKUP_COUNT++))
        done

        success "Deleted ${BACKUP_COUNT} old backup(s)"
    fi

    echo ""
}

# Main backup logic
case "${BACKUP_TYPE}" in
    ondemand)
        create_ondemand_backup
        ;;
    export)
        export_to_s3
        ;;
    pitr)
        enable_pitr
        ;;
    list)
        list_backups
        ;;
    clean)
        clean_old_backups
        ;;
    full)
        info "Performing full backup (on-demand + export)..."
        create_ondemand_backup
        export_to_s3
        ;;
    *)
        error "Unknown backup type: ${BACKUP_TYPE}"
        echo "Valid types: ondemand, export, pitr, list, clean, full"
        exit 1
        ;;
esac

# Save backup metadata
METADATA_FILE="${PROJECT_ROOT}/.backups/${ENVIRONMENT}/${BACKUP_NAME}.json"
mkdir -p "$(dirname ${METADATA_FILE})"

cat > "${METADATA_FILE}" <<EOF
{
    "backup_name": "${BACKUP_NAME}",
    "environment": "${ENVIRONMENT}",
    "table_name": "${DYNAMODB_TABLE}",
    "backup_type": "${BACKUP_TYPE}",
    "timestamp": "${TIMESTAMP}",
    "table_size_mb": ${TABLE_SIZE_MB},
    "region": "${REGION}",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

success "Backup metadata saved: ${METADATA_FILE}"

echo ""
echo "========================================="
echo "Backup Complete!"
echo "========================================="
echo ""
echo "To restore from this backup:"
echo "  aws dynamodb restore-table-from-backup \\"
echo "    --target-table-name ${DYNAMODB_TABLE}-restored \\"
echo "    --backup-arn <backup-arn> \\"
echo "    --region ${REGION}"
echo ""
echo "Or use Point-in-Time Recovery:"
echo "  aws dynamodb restore-table-to-point-in-time \\"
echo "    --source-table-name ${DYNAMODB_TABLE} \\"
echo "    --target-table-name ${DYNAMODB_TABLE}-restored \\"
echo "    --restore-date-time <timestamp> \\"
echo "    --region ${REGION}"
echo ""
