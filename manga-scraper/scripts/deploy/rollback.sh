#!/bin/bash
###############################################################################
# Rollback Script
# ===============
#
# Rolls back deployments to a previous version
# Supports:
# - Lambda function versions
# - Frontend deployments
# - Database migrations
#
# Usage: ./rollback.sh [component] [environment] [version]
# Components: lambda, frontend, all
# Example: ./rollback.sh lambda prod 5
###############################################################################

set -e  # Exit on error

# Configuration
COMPONENT="${1:-lambda}"
ENVIRONMENT="${2:-dev}"
VERSION="${3:-}"
REGION="${AWS_REGION:-us-east-1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Load environment variables
ENV_FILE="${PROJECT_ROOT}/.env.${ENVIRONMENT}"
if [ -f "${ENV_FILE}" ]; then
    source "${ENV_FILE}"
fi

FUNCTION_NAME="${LAMBDA_FUNCTION:-manga-scraper-${ENVIRONMENT}}"

echo "========================================="
echo "Rollback Script"
echo "========================================="
echo "Component:    ${COMPONENT}"
echo "Environment:  ${ENVIRONMENT}"
echo "Version:      ${VERSION:-latest}"
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

# Confirmation prompt
confirm_rollback() {
    echo ""
    echo -e "${YELLOW}WARNING: This will rollback ${COMPONENT} in ${ENVIRONMENT}${NC}"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Rollback cancelled"
        exit 0
    fi
}

# Rollback Lambda function
rollback_lambda() {
    echo "Rolling back Lambda function..."

    if ! command -v aws &> /dev/null; then
        error "AWS CLI is not installed"
        exit 1
    fi

    # Check if function exists
    if ! aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${REGION}" &> /dev/null; then
        error "Function ${FUNCTION_NAME} not found"
        exit 1
    fi

    # List recent versions if version not specified
    if [ -z "${VERSION}" ]; then
        info "Listing available versions..."
        echo ""

        aws lambda list-versions-by-function \
            --function-name "${FUNCTION_NAME}" \
            --region "${REGION}" \
            --query 'Versions[?Version!=`$LATEST`].[Version,Description,LastModified]' \
            --output table

        echo ""
        read -p "Enter version number to rollback to: " VERSION

        if [ -z "${VERSION}" ]; then
            error "No version specified"
            exit 1
        fi
    fi

    # Get current version
    CURRENT_VERSION=$(aws lambda get-alias \
        --function-name "${FUNCTION_NAME}" \
        --name "live" \
        --region "${REGION}" \
        --query 'FunctionVersion' \
        --output text 2>/dev/null || echo "\$LATEST")

    info "Current version: ${CURRENT_VERSION}"
    info "Target version:  ${VERSION}"

    confirm_rollback

    # Create backup of current configuration
    info "Backing up current configuration..."
    BACKUP_FILE="${PROJECT_ROOT}/.rollback-backup-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S).json"

    aws lambda get-function \
        --function-name "${FUNCTION_NAME}" \
        --region "${REGION}" > "${BACKUP_FILE}"

    success "Configuration backed up to: ${BACKUP_FILE}"

    # Update alias to point to target version
    info "Updating function alias..."

    if aws lambda get-alias --function-name "${FUNCTION_NAME}" --name "live" --region "${REGION}" &> /dev/null; then
        aws lambda update-alias \
            --function-name "${FUNCTION_NAME}" \
            --name "live" \
            --function-version "${VERSION}" \
            --description "Rolled back from ${CURRENT_VERSION} on $(date)" \
            --region "${REGION}" \
            --output text > /dev/null
    else
        aws lambda create-alias \
            --function-name "${FUNCTION_NAME}" \
            --name "live" \
            --function-version "${VERSION}" \
            --description "Rolled back from ${CURRENT_VERSION} on $(date)" \
            --region "${REGION}" \
            --output text > /dev/null
    fi

    success "Lambda function rolled back to version ${VERSION}"

    # Get function ARN
    FUNCTION_ARN=$(aws lambda get-alias \
        --function-name "${FUNCTION_NAME}" \
        --name "live" \
        --region "${REGION}" \
        --query 'AliasArn' \
        --output text)

    echo ""
    echo "Rollback complete!"
    echo "  Function: ${FUNCTION_NAME}"
    echo "  Old Version: ${CURRENT_VERSION}"
    echo "  New Version: ${VERSION}"
    echo "  Alias ARN: ${FUNCTION_ARN}"
    echo ""
}

# Rollback frontend deployment
rollback_frontend() {
    echo "Rolling back frontend deployment..."

    S3_FRONTEND_BUCKET="${PROJECT_NAME:-manga-scraper}-${ENVIRONMENT}-frontend"

    if ! aws s3 ls "s3://${S3_FRONTEND_BUCKET}" 2>/dev/null; then
        error "Frontend bucket not found: ${S3_FRONTEND_BUCKET}"
        exit 1
    fi

    # Check if versioning is enabled
    VERSIONING=$(aws s3api get-bucket-versioning \
        --bucket "${S3_FRONTEND_BUCKET}" \
        --query 'Status' \
        --output text)

    if [ "${VERSIONING}" != "Enabled" ]; then
        error "Bucket versioning is not enabled"
        echo "Cannot perform rollback without versioning"
        exit 1
    fi

    info "Bucket versioning: ${VERSIONING}"

    # List recent versions of index.html
    info "Listing recent frontend versions..."
    echo ""

    aws s3api list-object-versions \
        --bucket "${S3_FRONTEND_BUCKET}" \
        --prefix "index.html" \
        --max-items 10 \
        --query 'Versions[].[VersionId,LastModified,IsLatest]' \
        --output table

    echo ""
    read -p "Enter version ID to rollback to: " VERSION_ID

    if [ -z "${VERSION_ID}" ]; then
        error "No version ID specified"
        exit 1
    fi

    confirm_rollback

    # Restore the version
    info "Restoring frontend version..."

    # Download all objects from the specified version
    TEMP_DIR=$(mktemp -d)
    aws s3api list-object-versions \
        --bucket "${S3_FRONTEND_BUCKET}" \
        --query "Versions[?VersionId=='${VERSION_ID}'].Key" \
        --output text | while read -r key; do

        if [ -n "${key}" ]; then
            aws s3api get-object \
                --bucket "${S3_FRONTEND_BUCKET}" \
                --key "${key}" \
                --version-id "${VERSION_ID}" \
                "${TEMP_DIR}/${key}" > /dev/null 2>&1 || true
        fi
    done

    # Re-upload to make them current
    aws s3 sync "${TEMP_DIR}" "s3://${S3_FRONTEND_BUCKET}" --delete

    rm -rf "${TEMP_DIR}"

    success "Frontend rolled back to version ${VERSION_ID}"

    # Invalidate CloudFront cache
    if [ -n "${CLOUDFRONT_DISTRIBUTION_ID}" ]; then
        info "Invalidating CloudFront cache..."

        aws cloudfront create-invalidation \
            --distribution-id "${CLOUDFRONT_DISTRIBUTION_ID}" \
            --paths "/*" \
            --output text > /dev/null

        success "CloudFront cache invalidated"
    fi

    echo ""
    echo "Frontend rollback complete!"
    echo "  Bucket: ${S3_FRONTEND_BUCKET}"
    echo "  Version: ${VERSION_ID}"
    echo ""
}

# Rollback database migration
rollback_database() {
    echo "Database rollback..."

    warning "Database rollback not fully implemented"
    warning "This would typically involve:"
    echo "  1. Restore from Point-in-Time Recovery"
    echo "  2. Or restore from backup"
    echo ""

    if [ -z "${DYNAMODB_TABLE}" ]; then
        error "DYNAMODB_TABLE not set"
        exit 1
    fi

    # Check if PITR is enabled
    PITR_STATUS=$(aws dynamodb describe-continuous-backups \
        --table-name "${DYNAMODB_TABLE}" \
        --region "${REGION}" \
        --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus' \
        --output text)

    info "Point-in-Time Recovery Status: ${PITR_STATUS}"

    if [ "${PITR_STATUS}" != "ENABLED" ]; then
        warning "PITR not enabled for ${DYNAMODB_TABLE}"
    else
        info "You can restore to any point in time within the last 35 days"
        echo ""
        echo "To restore manually:"
        echo "  aws dynamodb restore-table-to-point-in-time \\"
        echo "    --source-table-name ${DYNAMODB_TABLE} \\"
        echo "    --target-table-name ${DYNAMODB_TABLE}-restored \\"
        echo "    --restore-date-time YYYY-MM-DDTHH:MM:SS \\"
        echo "    --region ${REGION}"
    fi

    echo ""
}

# Main rollback logic
case "${COMPONENT}" in
    lambda)
        rollback_lambda
        ;;
    frontend)
        rollback_frontend
        ;;
    database)
        rollback_database
        ;;
    all)
        info "Rolling back all components..."
        rollback_lambda
        rollback_frontend
        echo "Database rollback requires manual intervention"
        ;;
    *)
        error "Unknown component: ${COMPONENT}"
        echo "Valid components: lambda, frontend, database, all"
        exit 1
        ;;
esac

echo "========================================="
echo "Rollback Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Test the rolled back version"
echo "  2. Monitor logs for errors"
echo "  3. If issues persist, contact support"
echo ""
echo "To undo this rollback, redeploy:"
echo "  ./scripts/deploy/deploy-${COMPONENT}.sh ${ENVIRONMENT}"
echo ""
