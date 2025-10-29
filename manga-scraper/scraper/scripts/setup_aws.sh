#!/bin/bash
###############################################################################
# AWS Resource Setup Script
# ==========================
#
# Creates necessary AWS resources for manga scraper:
# - S3 bucket for image storage
# - DynamoDB table for metadata
# - IAM role for Lambda function
#
# Usage: ./setup_aws.sh [environment]
# Example: ./setup_aws.sh dev
###############################################################################

set -e  # Exit on error

# Configuration
ENVIRONMENT="${1:-dev}"
PROJECT_NAME="manga-scraper"
REGION="${AWS_REGION:-us-east-1}"

# Resource names
S3_BUCKET="${PROJECT_NAME}-${ENVIRONMENT}-images"
DYNAMODB_TABLE="${PROJECT_NAME}-${ENVIRONMENT}-metadata"
LAMBDA_ROLE="${PROJECT_NAME}-${ENVIRONMENT}-lambda-role"

echo "========================================="
echo "AWS Resource Setup for Manga Scraper"
echo "========================================="
echo "Environment: ${ENVIRONMENT}"
echo "Region: ${REGION}"
echo ""

# Check AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed"
    echo "Please install AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "Error: AWS credentials not configured"
    echo "Please run: aws configure"
    exit 1
fi

echo "AWS Account: $(aws sts get-caller-identity --query Account --output text)"
echo ""

# Create S3 bucket
echo "Creating S3 bucket: ${S3_BUCKET}"
if aws s3 ls "s3://${S3_BUCKET}" 2>/dev/null; then
    echo "  ✓ Bucket already exists"
else
    if [ "${REGION}" == "us-east-1" ]; then
        aws s3 mb "s3://${S3_BUCKET}"
    else
        aws s3 mb "s3://${S3_BUCKET}" --region "${REGION}"
    fi

    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket "${S3_BUCKET}" \
        --versioning-configuration Status=Enabled

    # Add lifecycle policy
    cat > /tmp/lifecycle-policy.json <<EOF
{
    "Rules": [
        {
            "Id": "DeleteOldVersions",
            "Status": "Enabled",
            "NoncurrentVersionExpiration": {
                "NoncurrentDays": 30
            }
        }
    ]
}
EOF

    aws s3api put-bucket-lifecycle-configuration \
        --bucket "${S3_BUCKET}" \
        --lifecycle-configuration file:///tmp/lifecycle-policy.json

    echo "  ✓ Bucket created with versioning enabled"
fi

# Create DynamoDB table
echo ""
echo "Creating DynamoDB table: ${DYNAMODB_TABLE}"
if aws dynamodb describe-table --table-name "${DYNAMODB_TABLE}" --region "${REGION}" &> /dev/null; then
    echo "  ✓ Table already exists"
else
    aws dynamodb create-table \
        --table-name "${DYNAMODB_TABLE}" \
        --attribute-definitions \
            AttributeName=PK,AttributeType=S \
            AttributeName=SK,AttributeType=S \
        --key-schema \
            AttributeName=PK,KeyType=HASH \
            AttributeName=SK,KeyType=RANGE \
        --billing-mode PAY_PER_REQUEST \
        --region "${REGION}" \
        --tags \
            Key=Environment,Value="${ENVIRONMENT}" \
            Key=Project,Value="${PROJECT_NAME}"

    # Wait for table to be active
    echo "  Waiting for table to be active..."
    aws dynamodb wait table-exists \
        --table-name "${DYNAMODB_TABLE}" \
        --region "${REGION}"

    echo "  ✓ Table created"
fi

# Create IAM role for Lambda
echo ""
echo "Creating IAM role: ${LAMBDA_ROLE}"

# Trust policy for Lambda
cat > /tmp/trust-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

# Create role
if aws iam get-role --role-name "${LAMBDA_ROLE}" &> /dev/null; then
    echo "  ✓ Role already exists"
else
    aws iam create-role \
        --role-name "${LAMBDA_ROLE}" \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        --description "Lambda execution role for ${PROJECT_NAME} ${ENVIRONMENT}"

    echo "  ✓ Role created"
fi

# Create and attach policy
cat > /tmp/lambda-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::${S3_BUCKET}",
                "arn:aws:s3:::${S3_BUCKET}/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": "arn:aws:dynamodb:${REGION}:*:table/${DYNAMODB_TABLE}"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:${REGION}:*:*"
        }
    ]
}
EOF

POLICY_NAME="${PROJECT_NAME}-${ENVIRONMENT}-lambda-policy"

echo "  Attaching policy: ${POLICY_NAME}"
aws iam put-role-policy \
    --role-name "${LAMBDA_ROLE}" \
    --policy-name "${POLICY_NAME}" \
    --policy-document file:///tmp/lambda-policy.json

echo "  ✓ Policy attached"

# Create .env file
echo ""
echo "Creating .env file..."
cat > .env <<EOF
# AWS Configuration
S3_BUCKET=${S3_BUCKET}
DYNAMODB_TABLE=${DYNAMODB_TABLE}
AWS_REGION=${REGION}

# Lambda Configuration
LAMBDA_ROLE_ARN=$(aws iam get-role --role-name "${LAMBDA_ROLE}" --query 'Role.Arn' --output text)

# Scraper Configuration
REQUESTS_PER_SECOND=0.5
MAX_RETRIES=3
WEBP_QUALITY=85
TARGET_IMAGE_SIZE_KB=200
LOG_LEVEL=INFO
EOF

echo "  ✓ .env file created"

# Cleanup temp files
rm -f /tmp/trust-policy.json /tmp/lambda-policy.json /tmp/lifecycle-policy.json

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Created resources:"
echo "  - S3 Bucket: ${S3_BUCKET}"
echo "  - DynamoDB Table: ${DYNAMODB_TABLE}"
echo "  - IAM Role: ${LAMBDA_ROLE}"
echo ""
echo "Environment variables saved to .env"
echo ""
echo "Next steps:"
echo "  1. Review and source .env file: source .env"
echo "  2. Deploy Lambda function: ./scripts/deploy.sh"
echo ""
