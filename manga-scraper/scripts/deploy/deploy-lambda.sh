#!/bin/bash
###############################################################################
# Lambda Deployment Script
# =========================
#
# Packages and deploys the manga scraper as an AWS Lambda function
# Includes dependency installation, packaging, and deployment
#
# Usage: ./deploy-lambda.sh [environment] [function-name]
# Example: ./deploy-lambda.sh dev manga-scraper-dev
###############################################################################

set -e  # Exit on error

# Configuration
ENVIRONMENT="${1:-dev}"
FUNCTION_NAME="${2:-manga-scraper-${ENVIRONMENT}}"
REGION="${AWS_REGION:-eu-west-3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Load environment variables
ENV_FILE="${PROJECT_ROOT}/.env.${ENVIRONMENT}"
if [ -f "${ENV_FILE}" ]; then
    source "${ENV_FILE}"
else
    echo "Error: Environment file not found: ${ENV_FILE}"
    echo "Please run ./scripts/setup/create-aws-resources.sh ${ENVIRONMENT}"
    exit 1
fi

echo "========================================="
echo "Lambda Deployment for Manga Scraper"
echo "========================================="
echo "Environment: ${ENVIRONMENT}"
echo "Function: ${FUNCTION_NAME}"
echo "Region: ${REGION}"
echo "Project Root: ${PROJECT_ROOT}"
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
echo "Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    error "AWS CLI is not installed"
    exit 1
fi
success "AWS CLI installed"

if ! command -v python3 &> /dev/null; then
    error "Python 3 is not installed"
    exit 1
fi
success "Python 3 installed"

if ! command -v zip &> /dev/null; then
    error "zip utility is not installed"
    exit 1
fi
success "zip utility installed"

# Check required variables
if [ -z "${S3_BUCKET}" ] || [ -z "${DYNAMODB_TABLE}" ] || [ -z "${LAMBDA_ROLE_ARN}" ]; then
    error "Missing required environment variables"
    echo "Please run: ./scripts/setup/create-aws-resources.sh ${ENVIRONMENT}"
    exit 1
fi
success "Environment variables loaded"
echo ""

# Create deployment package
echo "1. Creating deployment package..."

# Create temporary directory
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="${TEMP_DIR}/package"
mkdir -p "${PACKAGE_DIR}"

info "Working directory: ${TEMP_DIR}"

# Install dependencies
echo "  Installing dependencies..."
cd "${PROJECT_ROOT}/scraper"

# Check if lambda/requirements.txt exists
if [ ! -f "lambda/requirements.txt" ]; then
    error "lambda/requirements.txt not found"
    rm -rf "${TEMP_DIR}"
    exit 1
fi

# Use pip with Lambda-compatible platform flags
# This method has been tested and works reliably in WSL/Linux environments
info "Installing dependencies with Lambda-compatible platform flags..."
pip install -r lambda/requirements.txt -t "${PACKAGE_DIR}" --upgrade \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.11 \
  --only-binary=:all: 2>&1 | grep -E "(Successfully installed|Requirement already satisfied)" || true

success "Dependencies installed (Lambda-compatible)"

# Copy source code
echo "  Copying source code..."
if [ -d "src" ]; then
    cp -r src "${PACKAGE_DIR}/"
else
    error "src directory not found"
    rm -rf "${TEMP_DIR}"
    exit 1
fi

if [ -d "lambda" ]; then
    cp lambda/*.py "${PACKAGE_DIR}/" 2>/dev/null || true
else
    error "lambda directory not found"
    rm -rf "${TEMP_DIR}"
    exit 1
fi
success "Source code copied"

# Copy configuration files
echo "  Copying configuration..."
if [ -f "src/config.py" ]; then
    # Config already copied with src
    success "Configuration included"
fi

# Remove unnecessary files to reduce package size
echo "  Optimizing package size..."
cd "${PACKAGE_DIR}"
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
success "Package optimized"

# Create zip file
echo "  Creating zip archive..."
zip -r9 ../lambda-package.zip . > /dev/null
cd - > /dev/null

PACKAGE_FILE="${TEMP_DIR}/lambda-package.zip"
PACKAGE_SIZE=$(du -h "${PACKAGE_FILE}" | cut -f1)
success "Package created: ${PACKAGE_SIZE}"
echo ""

# Check if Lambda function exists
echo "2. Deploying Lambda function..."

FUNCTION_EXISTS=false
if aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${REGION}" &> /dev/null; then
    FUNCTION_EXISTS=true
fi

if [ "${FUNCTION_EXISTS}" = true ]; then
    info "Updating existing Lambda function..."

    # Update function code
    aws lambda update-function-code \
        --function-name "${FUNCTION_NAME}" \
        --zip-file "fileb://${PACKAGE_FILE}" \
        --region "${REGION}" \
        --output text > /dev/null

    success "Function code updated"

    # Wait for update to complete
    echo "  Waiting for update to complete..."
    aws lambda wait function-updated \
        --function-name "${FUNCTION_NAME}" \
        --region "${REGION}"

    # Update configuration
    aws lambda update-function-configuration \
        --function-name "${FUNCTION_NAME}" \
        --environment "Variables={
            S3_BUCKET=${S3_BUCKET},
            DYNAMODB_TABLE=${DYNAMODB_TABLE},
            REQUESTS_PER_SECOND=${REQUESTS_PER_SECOND:-0.5},
            MAX_RETRIES=${MAX_RETRIES:-3},
            RETRY_DELAY=${RETRY_DELAY:-5},
            WEBP_QUALITY=${WEBP_QUALITY:-85},
            TARGET_IMAGE_SIZE_KB=${TARGET_IMAGE_SIZE_KB:-200},
            MAX_IMAGE_SIZE_KB=${MAX_IMAGE_SIZE_KB:-500},
            LOG_LEVEL=${LOG_LEVEL:-INFO},
            ENABLE_DUPLICATE_DETECTION=${ENABLE_DUPLICATE_DETECTION:-true},
            ENABLE_IMAGE_OPTIMIZATION=${ENABLE_IMAGE_OPTIMIZATION:-true}
        }" \
        --timeout 300 \
        --memory-size 1024 \
        --region "${REGION}" \
        --output text > /dev/null

    success "Function configuration updated"

else
    info "Creating new Lambda function..."

    # Wait for IAM role to be ready
    echo "  Waiting for IAM role propagation..."
    sleep 10

    aws lambda create-function \
        --function-name "${FUNCTION_NAME}" \
        --runtime python3.11 \
        --role "${LAMBDA_ROLE_ARN}" \
        --handler handler.lambda_handler \
        --zip-file "fileb://${PACKAGE_FILE}" \
        --timeout 300 \
        --memory-size 1024 \
        --environment "Variables={
            S3_BUCKET=${S3_BUCKET},
            DYNAMODB_TABLE=${DYNAMODB_TABLE},
            REQUESTS_PER_SECOND=${REQUESTS_PER_SECOND:-0.5},
            MAX_RETRIES=${MAX_RETRIES:-3},
            RETRY_DELAY=${RETRY_DELAY:-5},
            WEBP_QUALITY=${WEBP_QUALITY:-85},
            TARGET_IMAGE_SIZE_KB=${TARGET_IMAGE_SIZE_KB:-200},
            MAX_IMAGE_SIZE_KB=${MAX_IMAGE_SIZE_KB:-500},
            LOG_LEVEL=${LOG_LEVEL:-INFO},
            ENABLE_DUPLICATE_DETECTION=${ENABLE_DUPLICATE_DETECTION:-true},
            ENABLE_IMAGE_OPTIMIZATION=${ENABLE_IMAGE_OPTIMIZATION:-true}
        }" \
        --region "${REGION}" \
        --tags "Environment=${ENVIRONMENT},Project=manga-scraper,ManagedBy=script" \
        --description "Manga scraper Lambda function for ${ENVIRONMENT}" \
        --output text > /dev/null

    success "Function created"
fi

# Wait for function to be ready
echo "  Waiting for function to be ready..."
aws lambda wait function-updated \
    --function-name "${FUNCTION_NAME}" \
    --region "${REGION}"

success "Function is ready"
echo ""

# Get function details
echo "3. Retrieving function information..."

FUNCTION_ARN=$(aws lambda get-function \
    --function-name "${FUNCTION_NAME}" \
    --region "${REGION}" \
    --query 'Configuration.FunctionArn' \
    --output text)

FUNCTION_SIZE=$(aws lambda get-function \
    --function-name "${FUNCTION_NAME}" \
    --region "${REGION}" \
    --query 'Configuration.CodeSize' \
    --output text)

FUNCTION_RUNTIME=$(aws lambda get-function \
    --function-name "${FUNCTION_NAME}" \
    --region "${REGION}" \
    --query 'Configuration.Runtime' \
    --output text)

FUNCTION_MEMORY=$(aws lambda get-function \
    --function-name "${FUNCTION_NAME}" \
    --region "${REGION}" \
    --query 'Configuration.MemorySize' \
    --output text)

FUNCTION_TIMEOUT=$(aws lambda get-function \
    --function-name "${FUNCTION_NAME}" \
    --region "${REGION}" \
    --query 'Configuration.Timeout' \
    --output text)

success "Function information retrieved"
echo ""

# Create version and alias (optional)
if [ "${ENVIRONMENT}" = "prod" ]; then
    echo "4. Creating version and alias..."

    VERSION=$(aws lambda publish-version \
        --function-name "${FUNCTION_NAME}" \
        --description "Deployed on $(date -u +%Y-%m-%d)" \
        --region "${REGION}" \
        --query 'Version' \
        --output text)

    success "Version created: ${VERSION}"

    # Update or create alias
    if aws lambda get-alias --function-name "${FUNCTION_NAME}" --name "live" --region "${REGION}" &> /dev/null; then
        aws lambda update-alias \
            --function-name "${FUNCTION_NAME}" \
            --name "live" \
            --function-version "${VERSION}" \
            --region "${REGION}" \
            --output text > /dev/null
        success "Alias 'live' updated to version ${VERSION}"
    else
        aws lambda create-alias \
            --function-name "${FUNCTION_NAME}" \
            --name "live" \
            --function-version "${VERSION}" \
            --region "${REGION}" \
            --output text > /dev/null
        success "Alias 'live' created for version ${VERSION}"
    fi
    echo ""
fi

# Cleanup
rm -rf "${TEMP_DIR}"
success "Cleanup complete"
echo ""

# Display summary
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Function Details:"
echo "  Name:        ${FUNCTION_NAME}"
echo "  ARN:         ${FUNCTION_ARN}"
echo "  Runtime:     ${FUNCTION_RUNTIME}"
echo "  Memory:      ${FUNCTION_MEMORY} MB"
echo "  Timeout:     ${FUNCTION_TIMEOUT} seconds"
echo "  Code Size:   $((FUNCTION_SIZE / 1024 / 1024)) MB"
echo "  Environment: ${ENVIRONMENT}"
echo ""
echo "Environment Variables:"
echo "  S3_BUCKET:          ${S3_BUCKET}"
echo "  DYNAMODB_TABLE:     ${DYNAMODB_TABLE}"
echo "  AWS_REGION:         ${REGION}"
echo "  LOG_LEVEL:          ${LOG_LEVEL:-INFO}"
echo ""
echo "Test the function with:"
echo "  aws lambda invoke \\"
echo "    --function-name ${FUNCTION_NAME} \\"
echo "    --region ${REGION} \\"
echo "    --payload '{\"action\":\"health_check\"}' \\"
echo "    response.json"
echo ""
echo "View logs with:"
echo "  aws logs tail /aws/lambda/${FUNCTION_NAME} --follow --region ${REGION}"
echo ""
