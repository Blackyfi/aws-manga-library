#!/bin/bash
###############################################################################
# Clean Old Images Script
# ========================
#
# Cleans up old and unused manga images from S3
# Removes:
# - Images older than retention period
# - Orphaned images (no metadata reference)
# - Duplicate images
# - Images from deleted manga
#
# Usage: ./clean-old-images.sh [environment] [mode]
# Modes: dry-run, execute
# Example: ./clean-old-images.sh prod dry-run
###############################################################################

set -e  # Exit on error

# Configuration
ENVIRONMENT="${1:-dev}"
MODE="${2:-dry-run}"
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

# Retention settings (days)
RETENTION_DAYS=${IMAGE_RETENTION_DAYS:-90}
ORPHAN_RETENTION_DAYS=${ORPHAN_RETENTION_DAYS:-30}

echo "========================================="
echo "Clean Old Images"
echo "========================================="
echo "Environment:     ${ENVIRONMENT}"
echo "S3 Bucket:       ${S3_BUCKET}"
echo "Mode:            ${MODE}"
echo "Retention:       ${RETENTION_DAYS} days"
echo "Region:          ${REGION}"
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

# Verify bucket exists
if ! aws s3 ls "s3://${S3_BUCKET}" &> /dev/null; then
    error "Bucket ${S3_BUCKET} not found"
    exit 1
fi

success "Bucket verified"
echo ""

# Calculate cutoff date
CUTOFF_DATE=$(date -u -d "${RETENTION_DAYS} days ago" '+%Y-%m-%d' 2>/dev/null || date -u -v-${RETENTION_DAYS}d '+%Y-%m-%d')
ORPHAN_CUTOFF=$(date -u -d "${ORPHAN_RETENTION_DAYS} days ago" '+%Y-%m-%d' 2>/dev/null || date -u -v-${ORPHAN_RETENTION_DAYS}d '+%Y-%m-%d')

info "Images last modified before ${CUTOFF_DATE} will be considered for deletion"
echo ""

# Create temporary directory for processing
TEMP_DIR=$(mktemp -d)
trap "rm -rf ${TEMP_DIR}" EXIT

# Function to get bucket size
get_bucket_size() {
    aws s3 ls "s3://${S3_BUCKET}" --recursive --summarize | grep "Total Size" | awk '{print $3}'
}

# Function to list old images
list_old_images() {
    info "Scanning for old images..."

    aws s3api list-objects-v2 \
        --bucket "${S3_BUCKET}" \
        --query "Contents[?LastModified<='${CUTOFF_DATE}'].Key" \
        --output text > "${TEMP_DIR}/old_images.txt"

    OLD_COUNT=$(wc -l < "${TEMP_DIR}/old_images.txt" | tr -d ' ')

    if [ "${OLD_COUNT}" -gt 0 ]; then
        success "Found ${OLD_COUNT} images older than ${RETENTION_DAYS} days"
    else
        info "No old images found"
    fi
}

# Function to find orphaned images
find_orphaned_images() {
    info "Scanning for orphaned images..."

    # Get all image keys from S3
    aws s3api list-objects-v2 \
        --bucket "${S3_BUCKET}" \
        --query "Contents[].Key" \
        --output text | tr '\t' '\n' > "${TEMP_DIR}/all_images.txt"

    # Get all image references from DynamoDB
    aws dynamodb scan \
        --table-name "${DYNAMODB_TABLE}" \
        --projection-expression "Images" \
        --region "${REGION}" \
        --output json | \
        jq -r '.Items[].Images.L[]?.S // empty' 2>/dev/null > "${TEMP_DIR}/referenced_images.txt" || echo "" > "${TEMP_DIR}/referenced_images.txt"

    # Find images not in DynamoDB
    sort "${TEMP_DIR}/all_images.txt" > "${TEMP_DIR}/all_sorted.txt"
    sort "${TEMP_DIR}/referenced_images.txt" > "${TEMP_DIR}/ref_sorted.txt"
    comm -23 "${TEMP_DIR}/all_sorted.txt" "${TEMP_DIR}/ref_sorted.txt" > "${TEMP_DIR}/orphaned.txt"

    ORPHAN_COUNT=$(wc -l < "${TEMP_DIR}/orphaned.txt" | tr -d ' ')

    if [ "${ORPHAN_COUNT}" -gt 0 ]; then
        warning "Found ${ORPHAN_COUNT} orphaned images"
    else
        info "No orphaned images found"
    fi
}

# Function to identify duplicates
find_duplicate_images() {
    info "Scanning for duplicate images..."

    # Query DynamoDB for images with duplicate hashes
    aws dynamodb scan \
        --table-name "${DYNAMODB_TABLE}" \
        --filter-expression "attribute_exists(ImageHash)" \
        --projection-expression "PK,SK,ImageHash,S3Key" \
        --region "${REGION}" \
        --output json > "${TEMP_DIR}/images_with_hash.json"

    # Process with jq to find duplicates
    jq -r '.Items[] | "\(.ImageHash.S)\t\(.S3Key.S)"' "${TEMP_DIR}/images_with_hash.json" 2>/dev/null | \
        sort | \
        uniq -d -w 64 > "${TEMP_DIR}/duplicates.txt" || echo "" > "${TEMP_DIR}/duplicates.txt"

    DUPLICATE_COUNT=$(wc -l < "${TEMP_DIR}/duplicates.txt" | tr -d ' ')

    if [ "${DUPLICATE_COUNT}" -gt 0 ]; then
        warning "Found ${DUPLICATE_COUNT} duplicate image groups"
    else
        info "No duplicate images found"
    fi
}

# Function to calculate savings
calculate_savings() {
    local file="$1"
    local total_size=0

    if [ ! -s "${file}" ]; then
        echo "0"
        return
    fi

    while IFS= read -r key; do
        if [ -n "${key}" ]; then
            size=$(aws s3api head-object \
                --bucket "${S3_BUCKET}" \
                --key "${key}" \
                --query 'ContentLength' \
                --output text 2>/dev/null || echo "0")
            total_size=$((total_size + size))
        fi
    done < "${file}"

    echo "$((total_size / 1024 / 1024))"
}

# Function to delete images
delete_images() {
    local file="$1"
    local description="$2"
    local count=0

    if [ ! -s "${file}" ]; then
        info "No ${description} to delete"
        return
    fi

    info "Processing ${description}..."

    while IFS= read -r key; do
        if [ -n "${key}" ]; then
            if [ "${MODE}" == "execute" ]; then
                aws s3 rm "s3://${S3_BUCKET}/${key}" 2>/dev/null && ((count++)) || true
            else
                echo "  Would delete: ${key}"
                ((count++))
            fi
        fi
    done < "${file}"

    if [ "${MODE}" == "execute" ]; then
        success "Deleted ${count} ${description}"
    else
        info "Would delete ${count} ${description}"
    fi
}

# Get initial bucket size
INITIAL_SIZE=$(get_bucket_size)
INITIAL_SIZE_MB=$((INITIAL_SIZE / 1024 / 1024))

info "Current bucket size: ${INITIAL_SIZE_MB} MB"
echo ""

# Perform cleanup operations
echo "1. Finding old images..."
list_old_images
OLD_SIZE=$(calculate_savings "${TEMP_DIR}/old_images.txt")
echo "  Potential savings: ${OLD_SIZE} MB"
echo ""

echo "2. Finding orphaned images..."
find_orphaned_images
ORPHAN_SIZE=$(calculate_savings "${TEMP_DIR}/orphaned.txt")
echo "  Potential savings: ${ORPHAN_SIZE} MB"
echo ""

echo "3. Finding duplicate images..."
find_duplicate_images
DUPLICATE_SIZE=$(calculate_savings "${TEMP_DIR}/duplicates.txt")
echo "  Potential savings: ${DUPLICATE_SIZE} MB"
echo ""

# Calculate total savings
TOTAL_SAVINGS=$((OLD_SIZE + ORPHAN_SIZE + DUPLICATE_SIZE))

echo "========================================="
echo "Cleanup Summary"
echo "========================================="
echo "Old images:        $(wc -l < ${TEMP_DIR}/old_images.txt | tr -d ' ') files (${OLD_SIZE} MB)"
echo "Orphaned images:   $(wc -l < ${TEMP_DIR}/orphaned.txt | tr -d ' ') files (${ORPHAN_SIZE} MB)"
echo "Duplicate images:  $(wc -l < ${TEMP_DIR}/duplicates.txt | tr -d ' ') files (${DUPLICATE_SIZE} MB)"
echo "----------------------------------------"
echo "Total savings:     ${TOTAL_SAVINGS} MB"
echo ""

if [ "${MODE}" == "dry-run" ]; then
    warning "Running in DRY-RUN mode - no files will be deleted"
    echo ""
    echo "To execute cleanup, run:"
    echo "  $0 ${ENVIRONMENT} execute"
    echo ""
else
    warning "Running in EXECUTE mode - files will be PERMANENTLY deleted"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        info "Cleanup cancelled"
        exit 0
    fi

    echo "Starting cleanup..."
    echo ""

    # Delete old images
    if [ -s "${TEMP_DIR}/old_images.txt" ]; then
        delete_images "${TEMP_DIR}/old_images.txt" "old images"
        echo ""
    fi

    # Delete orphaned images
    if [ -s "${TEMP_DIR}/orphaned.txt" ]; then
        delete_images "${TEMP_DIR}/orphaned.txt" "orphaned images"
        echo ""
    fi

    # Delete duplicates (keep first occurrence)
    if [ -s "${TEMP_DIR}/duplicates.txt" ]; then
        delete_images "${TEMP_DIR}/duplicates.txt" "duplicate images"
        echo ""
    fi

    # Get final bucket size
    FINAL_SIZE=$(get_bucket_size)
    FINAL_SIZE_MB=$((FINAL_SIZE / 1024 / 1024))
    ACTUAL_SAVINGS=$((INITIAL_SIZE_MB - FINAL_SIZE_MB))

    echo "========================================="
    echo "Cleanup Complete!"
    echo "========================================="
    echo "Initial size:      ${INITIAL_SIZE_MB} MB"
    echo "Final size:        ${FINAL_SIZE_MB} MB"
    echo "Space freed:       ${ACTUAL_SAVINGS} MB"
    echo ""
fi

# Save cleanup report
REPORT_FILE="${PROJECT_ROOT}/.reports/cleanup-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S).json"
mkdir -p "$(dirname ${REPORT_FILE})"

cat > "${REPORT_FILE}" <<EOF
{
    "environment": "${ENVIRONMENT}",
    "bucket": "${S3_BUCKET}",
    "mode": "${MODE}",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "retention_days": ${RETENTION_DAYS},
    "statistics": {
        "old_images": $(wc -l < ${TEMP_DIR}/old_images.txt | tr -d ' '),
        "orphaned_images": $(wc -l < ${TEMP_DIR}/orphaned.txt | tr -d ' '),
        "duplicate_images": $(wc -l < ${TEMP_DIR}/duplicates.txt | tr -d ' '),
        "old_size_mb": ${OLD_SIZE},
        "orphan_size_mb": ${ORPHAN_SIZE},
        "duplicate_size_mb": ${DUPLICATE_SIZE},
        "total_savings_mb": ${TOTAL_SAVINGS}
    }
}
EOF

success "Report saved: ${REPORT_FILE}"
echo ""
