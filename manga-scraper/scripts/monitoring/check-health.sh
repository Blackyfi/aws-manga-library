#!/bin/bash
###############################################################################
# Health Check Script
# ====================
#
# Performs comprehensive health checks on all system components
# Checks:
# - Lambda function status
# - S3 bucket accessibility
# - DynamoDB table status
# - CloudFront distribution
# - API endpoints
#
# Usage: ./check-health.sh [environment]
# Example: ./check-health.sh prod
###############################################################################

set -e  # Exit on error (disable for health checks)
set +e  # Continue on errors to check all components

# Configuration
ENVIRONMENT="${1:-dev}"
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
echo "System Health Check"
echo "========================================="
echo "Environment: ${ENVIRONMENT}"
echo "Region:      ${REGION}"
echo "Time:        $(date)"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Status trackers
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

pass() {
    echo -e "${GREEN}✓ PASS${NC} $1"
    ((PASSED_CHECKS++))
    ((TOTAL_CHECKS++))
}

fail() {
    echo -e "${RED}✗ FAIL${NC} $1"
    ((FAILED_CHECKS++))
    ((TOTAL_CHECKS++))
}

warn() {
    echo -e "${YELLOW}⚠ WARN${NC} $1"
    ((WARNING_CHECKS++))
    ((TOTAL_CHECKS++))
}

info() {
    echo -e "${BLUE}ℹ INFO${NC} $1"
}

# Check AWS CLI
echo "1. AWS CLI"
echo "----------------------------------------"
if command -v aws &> /dev/null; then
    AWS_VERSION=$(aws --version 2>&1 | cut -d' ' -f1)
    pass "AWS CLI installed: ${AWS_VERSION}"

    if aws sts get-caller-identity &> /dev/null; then
        AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
        AWS_USER=$(aws sts get-caller-identity --query Arn --output text)
        pass "AWS credentials configured"
        info "Account: ${AWS_ACCOUNT}"
        info "User: ${AWS_USER}"
    else
        fail "AWS credentials not configured"
    fi
else
    fail "AWS CLI not installed"
fi
echo ""

# Check Lambda function
echo "2. Lambda Function"
echo "----------------------------------------"
if [ -n "${FUNCTION_NAME}" ]; then
    if aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${REGION}" &> /dev/null; then
        pass "Lambda function exists: ${FUNCTION_NAME}"

        # Get function details
        FUNC_STATE=$(aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${REGION}" --query 'Configuration.State' --output text)
        FUNC_STATUS=$(aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${REGION}" --query 'Configuration.LastUpdateStatus' --output text)
        FUNC_RUNTIME=$(aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${REGION}" --query 'Configuration.Runtime' --output text)
        FUNC_MEMORY=$(aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${REGION}" --query 'Configuration.MemorySize' --output text)

        if [ "${FUNC_STATE}" == "Active" ]; then
            pass "Function state: ${FUNC_STATE}"
        else
            fail "Function state: ${FUNC_STATE}"
        fi

        if [ "${FUNC_STATUS}" == "Successful" ]; then
            pass "Last update: ${FUNC_STATUS}"
        else
            warn "Last update: ${FUNC_STATUS}"
        fi

        info "Runtime: ${FUNC_RUNTIME}"
        info "Memory: ${FUNC_MEMORY} MB"

        # Test function invocation
        info "Testing function invocation..."
        INVOKE_RESULT=$(aws lambda invoke \
            --function-name "${FUNCTION_NAME}" \
            --region "${REGION}" \
            --payload '{"action":"health_check"}' \
            /tmp/lambda-response.json 2>&1)

        if [ $? -eq 0 ]; then
            pass "Function invocation successful"
        else
            fail "Function invocation failed"
        fi
    else
        fail "Lambda function not found: ${FUNCTION_NAME}"
    fi
else
    warn "Lambda function name not configured"
fi
echo ""

# Check S3 bucket
echo "3. S3 Storage"
echo "----------------------------------------"
if [ -n "${S3_BUCKET}" ]; then
    if aws s3 ls "s3://${S3_BUCKET}" &> /dev/null; then
        pass "S3 bucket accessible: ${S3_BUCKET}"

        # Get bucket size
        BUCKET_SIZE=$(aws s3 ls "s3://${S3_BUCKET}" --recursive --summarize 2>/dev/null | grep "Total Size" | awk '{print $3}')
        BUCKET_SIZE_MB=$((BUCKET_SIZE / 1024 / 1024))
        OBJECT_COUNT=$(aws s3 ls "s3://${S3_BUCKET}" --recursive --summarize 2>/dev/null | grep "Total Objects" | awk '{print $3}')

        info "Bucket size: ${BUCKET_SIZE_MB} MB"
        info "Object count: ${OBJECT_COUNT}"

        # Check versioning
        VERSIONING=$(aws s3api get-bucket-versioning --bucket "${S3_BUCKET}" --query 'Status' --output text)
        if [ "${VERSIONING}" == "Enabled" ]; then
            pass "Versioning enabled"
        else
            warn "Versioning not enabled"
        fi

        # Test write access
        TEST_FILE="health-check-$(date +%s).txt"
        if echo "Health check test" | aws s3 cp - "s3://${S3_BUCKET}/${TEST_FILE}" 2>/dev/null; then
            pass "Write access confirmed"
            aws s3 rm "s3://${S3_BUCKET}/${TEST_FILE}" &> /dev/null
        else
            fail "No write access to bucket"
        fi
    else
        fail "S3 bucket not accessible: ${S3_BUCKET}"
    fi
else
    warn "S3 bucket name not configured"
fi

# Check backup bucket
if [ -n "${S3_BACKUP_BUCKET}" ]; then
    if aws s3 ls "s3://${S3_BACKUP_BUCKET}" &> /dev/null; then
        pass "Backup bucket accessible: ${S3_BACKUP_BUCKET}"
    else
        warn "Backup bucket not accessible: ${S3_BACKUP_BUCKET}"
    fi
fi
echo ""

# Check DynamoDB table
echo "4. DynamoDB Database"
echo "----------------------------------------"
if [ -n "${DYNAMODB_TABLE}" ]; then
    if aws dynamodb describe-table --table-name "${DYNAMODB_TABLE}" --region "${REGION}" &> /dev/null; then
        pass "DynamoDB table exists: ${DYNAMODB_TABLE}"

        # Get table details
        TABLE_STATUS=$(aws dynamodb describe-table --table-name "${DYNAMODB_TABLE}" --region "${REGION}" --query 'Table.TableStatus' --output text)
        ITEM_COUNT=$(aws dynamodb describe-table --table-name "${DYNAMODB_TABLE}" --region "${REGION}" --query 'Table.ItemCount' --output text)
        TABLE_SIZE=$(aws dynamodb describe-table --table-name "${DYNAMODB_TABLE}" --region "${REGION}" --query 'Table.TableSizeBytes' --output text)
        TABLE_SIZE_MB=$((TABLE_SIZE / 1024 / 1024))

        if [ "${TABLE_STATUS}" == "ACTIVE" ]; then
            pass "Table status: ${TABLE_STATUS}"
        else
            fail "Table status: ${TABLE_STATUS}"
        fi

        info "Item count: ${ITEM_COUNT}"
        info "Table size: ${TABLE_SIZE_MB} MB"

        # Check PITR
        PITR_STATUS=$(aws dynamodb describe-continuous-backups \
            --table-name "${DYNAMODB_TABLE}" \
            --region "${REGION}" \
            --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus' \
            --output text 2>/dev/null || echo "DISABLED")

        if [ "${PITR_STATUS}" == "ENABLED" ]; then
            pass "Point-in-Time Recovery enabled"
        else
            warn "Point-in-Time Recovery not enabled"
        fi

        # Test read access
        if aws dynamodb scan --table-name "${DYNAMODB_TABLE}" --region "${REGION}" --limit 1 &> /dev/null; then
            pass "Read access confirmed"
        else
            fail "No read access to table"
        fi
    else
        fail "DynamoDB table not found: ${DYNAMODB_TABLE}"
    fi
else
    warn "DynamoDB table name not configured"
fi
echo ""

# Check CloudWatch Logs
echo "5. CloudWatch Logs"
echo "----------------------------------------"
if [ -n "${FUNCTION_NAME}" ]; then
    LOG_GROUP="/aws/lambda/${FUNCTION_NAME}"

    if aws logs describe-log-groups --log-group-name-prefix "${LOG_GROUP}" --region "${REGION}" &> /dev/null; then
        pass "Log group exists: ${LOG_GROUP}"

        # Get recent errors
        RECENT_ERRORS=$(aws logs filter-log-events \
            --log-group-name "${LOG_GROUP}" \
            --region "${REGION}" \
            --filter-pattern "ERROR" \
            --start-time $(($(date +%s) * 1000 - 3600000)) \
            --query 'events' \
            --output json 2>/dev/null | jq length 2>/dev/null || echo "0")

        if [ "${RECENT_ERRORS}" -eq 0 ]; then
            pass "No errors in last hour"
        else
            warn "Found ${RECENT_ERRORS} errors in last hour"
        fi
    else
        warn "Log group not found: ${LOG_GROUP}"
    fi
fi
echo ""

# Check CloudFront (if configured)
echo "6. CloudFront CDN"
echo "----------------------------------------"
if [ -n "${CLOUDFRONT_DISTRIBUTION_ID}" ]; then
    if aws cloudfront get-distribution --id "${CLOUDFRONT_DISTRIBUTION_ID}" &> /dev/null; then
        pass "CloudFront distribution exists"

        DIST_STATUS=$(aws cloudfront get-distribution \
            --id "${CLOUDFRONT_DISTRIBUTION_ID}" \
            --query 'Distribution.Status' \
            --output text)

        DIST_ENABLED=$(aws cloudfront get-distribution \
            --id "${CLOUDFRONT_DISTRIBUTION_ID}" \
            --query 'Distribution.DistributionConfig.Enabled' \
            --output text)

        if [ "${DIST_STATUS}" == "Deployed" ]; then
            pass "Distribution status: ${DIST_STATUS}"
        else
            warn "Distribution status: ${DIST_STATUS}"
        fi

        if [ "${DIST_ENABLED}" == "true" ]; then
            pass "Distribution enabled"
        else
            fail "Distribution disabled"
        fi
    else
        fail "CloudFront distribution not found"
    fi
else
    info "CloudFront not configured"
fi
echo ""

# Check system resources
echo "7. System Resources"
echo "----------------------------------------"

# Check disk space
DISK_USAGE=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "${DISK_USAGE}" -lt 80 ]; then
    pass "Disk usage: ${DISK_USAGE}%"
elif [ "${DISK_USAGE}" -lt 90 ]; then
    warn "Disk usage: ${DISK_USAGE}%"
else
    fail "Disk usage: ${DISK_USAGE}%"
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    pass "Python installed: ${PYTHON_VERSION}"
else
    warn "Python not installed"
fi

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    pass "Node.js installed: ${NODE_VERSION}"
else
    warn "Node.js not installed"
fi

echo ""

# Generate summary
echo "========================================="
echo "Health Check Summary"
echo "========================================="
echo ""

HEALTH_SCORE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))

echo "Total Checks:    ${TOTAL_CHECKS}"
echo -e "Passed:          ${GREEN}${PASSED_CHECKS}${NC}"
echo -e "Failed:          ${RED}${FAILED_CHECKS}${NC}"
echo -e "Warnings:        ${YELLOW}${WARNING_CHECKS}${NC}"
echo ""
echo -e "Health Score:    ${HEALTH_SCORE}%"
echo ""

# Determine overall status
if [ "${FAILED_CHECKS}" -eq 0 ] && [ "${WARNING_CHECKS}" -eq 0 ]; then
    echo -e "${GREEN}✓ All systems operational${NC}"
    EXIT_CODE=0
elif [ "${FAILED_CHECKS}" -eq 0 ]; then
    echo -e "${YELLOW}⚠ System operational with warnings${NC}"
    EXIT_CODE=1
else
    echo -e "${RED}✗ System has failures${NC}"
    EXIT_CODE=2
fi

echo ""

# Save report
REPORT_FILE="${PROJECT_ROOT}/.reports/health-check-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S).json"
mkdir -p "$(dirname ${REPORT_FILE})"

cat > "${REPORT_FILE}" <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "environment": "${ENVIRONMENT}",
    "region": "${REGION}",
    "health_score": ${HEALTH_SCORE},
    "checks": {
        "total": ${TOTAL_CHECKS},
        "passed": ${PASSED_CHECKS},
        "failed": ${FAILED_CHECKS},
        "warnings": ${WARNING_CHECKS}
    },
    "components": {
        "lambda": "${FUNCTION_NAME}",
        "s3": "${S3_BUCKET}",
        "dynamodb": "${DYNAMODB_TABLE}",
        "cloudfront": "${CLOUDFRONT_DISTRIBUTION_ID:-N/A}"
    },
    "status": "$([ ${EXIT_CODE} -eq 0 ] && echo 'healthy' || ([ ${EXIT_CODE} -eq 1 ] && echo 'warning' || echo 'unhealthy'))"
}
EOF

info "Report saved: ${REPORT_FILE}"
echo ""

exit ${EXIT_CODE}
