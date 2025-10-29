#!/bin/bash
###############################################################################
# Lambda Deployment Script
# =========================
#
# Packages and deploys the manga scraper as an AWS Lambda function
#
# Usage: ./deploy.sh [environment] [function-name]
# Example: ./deploy.sh dev manga-scraper-dev
###############################################################################

set -e  # Exit on error

# Configuration
ENVIRONMENT="${1:-dev}"
FUNCTION_NAME="${2:-manga-scraper-${ENVIRONMENT}}"
REGION="${AWS_REGION:-us-east-1}"

echo "========================================="
echo "Lambda Deployment for Manga Scraper"
echo "========================================="
echo "Environment: ${ENVIRONMENT}"
echo "Function: ${FUNCTION_NAME}"
echo "Region: ${REGION}"
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed"
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    echo "Please run ./scripts/setup_aws.sh first"
    exit 1
fi

# Load environment variables
source .env

# Check required variables
if [ -z "${S3_BUCKET}" ] || [ -z "${DYNAMODB_TABLE}" ] || [ -z "${LAMBDA_ROLE_ARN}" ]; then
    echo "Error: Missing required environment variables"
    echo "Please run ./scripts/setup_aws.sh first"
    exit 1
fi

# Create deployment package
echo "Creating deployment package..."

# Create temporary directory
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="${TEMP_DIR}/package"
mkdir -p "${PACKAGE_DIR}"

echo "  Working directory: ${TEMP_DIR}"

# Install dependencies
echo "  Installing dependencies..."
pip install -r lambda/requirements.txt -t "${PACKAGE_DIR}" --quiet

# Copy source code
echo "  Copying source code..."
cp -r src "${PACKAGE_DIR}/"
cp -r lambda/* "${PACKAGE_DIR}/"

# Create zip file
echo "  Creating zip archive..."
cd "${PACKAGE_DIR}"
zip -r9 ../lambda-package.zip . > /dev/null
cd - > /dev/null

PACKAGE_FILE="${TEMP_DIR}/lambda-package.zip"
PACKAGE_SIZE=$(du -h "${PACKAGE_FILE}" | cut -f1)
echo "  ✓ Package created: ${PACKAGE_SIZE}"

# Check if Lambda function exists
echo ""
if aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${REGION}" &> /dev/null; then
    echo "Updating existing Lambda function..."

    aws lambda update-function-code \
        --function-name "${FUNCTION_NAME}" \
        --zip-file "fileb://${PACKAGE_FILE}" \
        --region "${REGION}" \
        --output text > /dev/null

    echo "  ✓ Function code updated"

    # Update configuration
    aws lambda update-function-configuration \
        --function-name "${FUNCTION_NAME}" \
        --environment "Variables={
            S3_BUCKET=${S3_BUCKET},
            DYNAMODB_TABLE=${DYNAMODB_TABLE},
            AWS_REGION=${REGION},
            REQUESTS_PER_SECOND=${REQUESTS_PER_SECOND:-0.5},
            MAX_RETRIES=${MAX_RETRIES:-3},
            WEBP_QUALITY=${WEBP_QUALITY:-85},
            TARGET_IMAGE_SIZE_KB=${TARGET_IMAGE_SIZE_KB:-200},
            LOG_LEVEL=${LOG_LEVEL:-INFO}
        }" \
        --timeout 300 \
        --memory-size 1024 \
        --region "${REGION}" \
        --output text > /dev/null

    echo "  ✓ Function configuration updated"

else
    echo "Creating new Lambda function..."

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
            AWS_REGION=${REGION},
            REQUESTS_PER_SECOND=${REQUESTS_PER_SECOND:-0.5},
            MAX_RETRIES=${MAX_RETRIES:-3},
            WEBP_QUALITY=${WEBP_QUALITY:-85},
            TARGET_IMAGE_SIZE_KB=${TARGET_IMAGE_SIZE_KB:-200},
            LOG_LEVEL=${LOG_LEVEL:-INFO}
        }" \
        --region "${REGION}" \
        --tags "Environment=${ENVIRONMENT},Project=manga-scraper" \
        --output text > /dev/null

    echo "  ✓ Function created"
fi

# Wait for function to be updated
echo "  Waiting for function to be ready..."
aws lambda wait function-updated \
    --function-name "${FUNCTION_NAME}" \
    --region "${REGION}"

# Get function info
FUNCTION_ARN=$(aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${REGION}" --query 'Configuration.FunctionArn' --output text)
FUNCTION_SIZE=$(aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${REGION}" --query 'Configuration.CodeSize' --output text)

# Cleanup
rm -rf "${TEMP_DIR}"
echo "  ✓ Cleanup complete"

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Function Details:"
echo "  Name: ${FUNCTION_NAME}"
echo "  ARN: ${FUNCTION_ARN}"
echo "  Size: $((FUNCTION_SIZE / 1024 / 1024)) MB"
echo "  Runtime: python3.11"
echo "  Memory: 1024 MB"
echo "  Timeout: 300 seconds"
echo ""
echo "Test the function:"
echo "  aws lambda invoke \\"
echo "    --function-name ${FUNCTION_NAME} \\"
echo "    --payload '{\"action\":\"list_manga\",\"source\":\"mangadex\",\"page\":1}' \\"
echo "    --region ${REGION} \\"
echo "    response.json"
echo ""
