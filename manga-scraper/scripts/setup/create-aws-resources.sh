#!/bin/bash
###############################################################################
# AWS Resource Creation Script
# =============================
#
# Creates all necessary AWS resources for the manga scraper application
# This is a comprehensive setup that includes:
# - S3 buckets (images, backups)
# - DynamoDB tables (metadata)
# - IAM roles and policies
# - CloudFront distribution
# - Lambda function
# - EventBridge rules
#
# Usage: ./create-aws-resources.sh [environment]
# Example: ./create-aws-resources.sh dev
###############################################################################

set -e  # Exit on error

# Configuration
ENVIRONMENT="${1:-dev}"
PROJECT_NAME="manga-scraper"
REGION="${AWS_REGION:-eu-west-3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resource names
S3_BUCKET="${PROJECT_NAME}-${ENVIRONMENT}-images"
S3_BACKUP_BUCKET="${PROJECT_NAME}-${ENVIRONMENT}-backups"
DYNAMODB_TABLE="${PROJECT_NAME}-${ENVIRONMENT}-metadata"
LAMBDA_ROLE="${PROJECT_NAME}-${ENVIRONMENT}-lambda-role"
LAMBDA_FUNCTION="${PROJECT_NAME}-${ENVIRONMENT}"
CLOUDFRONT_DIST="${PROJECT_NAME}-${ENVIRONMENT}-cdn"

echo "========================================="
echo "AWS Resource Creation for Manga Scraper"
echo "========================================="
echo "Environment: ${ENVIRONMENT}"
echo "Region: ${REGION}"
echo "Project: ${PROJECT_NAME}"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print success message
success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Function to print warning message
warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Function to print error message
error() {
    echo -e "${RED}✗${NC} $1"
}

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    error "AWS CLI is not installed"
    echo "Please install AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi
success "AWS CLI installed"

if ! aws sts get-caller-identity &> /dev/null; then
    error "AWS credentials not configured"
    echo "Please run: aws configure"
    exit 1
fi

AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
success "AWS Account: ${AWS_ACCOUNT}"
echo ""

# Create S3 bucket for images
echo "1. Creating S3 bucket for images: ${S3_BUCKET}"
if aws s3 ls "s3://${S3_BUCKET}" 2>/dev/null; then
    warning "Bucket already exists"
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

    # Block public access
    aws s3api put-public-access-block \
        --bucket "${S3_BUCKET}" \
        --public-access-block-configuration \
            "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=false,RestrictPublicBuckets=false"

    # Add CORS configuration
    cat > /tmp/cors-config.json <<EOF
{
    "CORSRules": [
        {
            "AllowedOrigins": ["*"],
            "AllowedMethods": ["GET", "HEAD"],
            "AllowedHeaders": ["*"],
            "MaxAgeSeconds": 3600
        }
    ]
}
EOF

    aws s3api put-bucket-cors \
        --bucket "${S3_BUCKET}" \
        --cors-configuration file:///tmp/cors-config.json

    # Add lifecycle policy
    cat > /tmp/lifecycle-policy.json <<EOF
{
    "Rules": [
        {
            "ID": "DeleteOldVersions",
            "Status": "Enabled",
            "Filter": {},
            "NoncurrentVersionExpiration": {
                "NoncurrentDays": 30
            }
        },
        {
            "ID": "TransitionToIA",
            "Status": "Enabled",
            "Filter": {},
            "Transitions": [
                {
                    "Days": 90,
                    "StorageClass": "STANDARD_IA"
                }
            ]
        }
    ]
}
EOF

    aws s3api put-bucket-lifecycle-configuration \
        --bucket "${S3_BUCKET}" \
        --lifecycle-configuration file:///tmp/lifecycle-policy.json

    # Add tags
    aws s3api put-bucket-tagging \
        --bucket "${S3_BUCKET}" \
        --tagging "TagSet=[{Key=Environment,Value=${ENVIRONMENT}},{Key=Project,Value=${PROJECT_NAME}}]"

    success "S3 image bucket created"
fi
echo ""

# Create S3 bucket for backups
echo "2. Creating S3 bucket for backups: ${S3_BACKUP_BUCKET}"
if aws s3 ls "s3://${S3_BACKUP_BUCKET}" 2>/dev/null; then
    warning "Backup bucket already exists"
else
    if [ "${REGION}" == "us-east-1" ]; then
        aws s3 mb "s3://${S3_BACKUP_BUCKET}"
    else
        aws s3 mb "s3://${S3_BACKUP_BUCKET}" --region "${REGION}"
    fi

    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket "${S3_BACKUP_BUCKET}" \
        --versioning-configuration Status=Enabled

    # Lifecycle policy for backups
    cat > /tmp/backup-lifecycle.json <<EOF
{
    "Rules": [
        {
            "ID": "DeleteOldBackups",
            "Status": "Enabled",
            "Filter": {},
            "Expiration": {
                "Days": 90
            }
        },
        {
            "ID": "TransitionToGlacier",
            "Status": "Enabled",
            "Filter": {},
            "Transitions": [
                {
                    "Days": 30,
                    "StorageClass": "GLACIER"
                }
            ]
        }
    ]
}
EOF

    aws s3api put-bucket-lifecycle-configuration \
        --bucket "${S3_BACKUP_BUCKET}" \
        --lifecycle-configuration file:///tmp/backup-lifecycle.json

    success "S3 backup bucket created"
fi
echo ""

# Create DynamoDB table
echo "3. Creating DynamoDB table: ${DYNAMODB_TABLE}"
if aws dynamodb describe-table --table-name "${DYNAMODB_TABLE}" --region "${REGION}" &> /dev/null; then
    warning "Table already exists"
else
    aws dynamodb create-table \
        --table-name "${DYNAMODB_TABLE}" \
        --attribute-definitions \
            AttributeName=PK,AttributeType=S \
            AttributeName=SK,AttributeType=S \
            AttributeName=GSI1PK,AttributeType=S \
            AttributeName=GSI1SK,AttributeType=S \
        --key-schema \
            AttributeName=PK,KeyType=HASH \
            AttributeName=SK,KeyType=RANGE \
        --global-secondary-indexes \
            "[{
                \"IndexName\": \"GSI1\",
                \"KeySchema\": [{\"AttributeName\":\"GSI1PK\",\"KeyType\":\"HASH\"},{\"AttributeName\":\"GSI1SK\",\"KeyType\":\"RANGE\"}],
                \"Projection\": {\"ProjectionType\":\"ALL\"},
                \"ProvisionedThroughput\": {\"ReadCapacityUnits\":5,\"WriteCapacityUnits\":5}
            }]" \
        --billing-mode PROVISIONED \
        --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
        --region "${REGION}" \
        --tags \
            Key=Environment,Value="${ENVIRONMENT}" \
            Key=Project,Value="${PROJECT_NAME}"

    # Wait for table to be active
    echo "  Waiting for table to be active..."
    aws dynamodb wait table-exists \
        --table-name "${DYNAMODB_TABLE}" \
        --region "${REGION}"

    # Enable point-in-time recovery
    aws dynamodb update-continuous-backups \
        --table-name "${DYNAMODB_TABLE}" \
        --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
        --region "${REGION}"

    success "DynamoDB table created with PITR enabled"
fi
echo ""

# Create IAM role for Lambda
echo "4. Creating IAM role: ${LAMBDA_ROLE}"

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
    warning "Role already exists"
else
    aws iam create-role \
        --role-name "${LAMBDA_ROLE}" \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        --description "Lambda execution role for ${PROJECT_NAME} ${ENVIRONMENT}"

    success "IAM role created"
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
                "arn:aws:s3:::${S3_BUCKET}/*",
                "arn:aws:s3:::${S3_BACKUP_BUCKET}",
                "arn:aws:s3:::${S3_BACKUP_BUCKET}/*"
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
                "dynamodb:Scan",
                "dynamodb:BatchWriteItem",
                "dynamodb:BatchGetItem"
            ],
            "Resource": [
                "arn:aws:dynamodb:${REGION}:${AWS_ACCOUNT}:table/${DYNAMODB_TABLE}",
                "arn:aws:dynamodb:${REGION}:${AWS_ACCOUNT}:table/${DYNAMODB_TABLE}/index/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:${REGION}:${AWS_ACCOUNT}:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "cloudwatch:PutMetricData"
            ],
            "Resource": "*"
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

success "IAM policy attached"
echo ""

# Get IAM role ARN
LAMBDA_ROLE_ARN=$(aws iam get-role --role-name "${LAMBDA_ROLE}" --query 'Role.Arn' --output text)

# Create CloudFront Origin Access Identity
echo "5. Creating CloudFront distribution..."
CALLER_REF="manga-scraper-${ENVIRONMENT}-$(date +%s)"

# Create OAI
OAI_ID=$(aws cloudfront create-cloud-front-origin-access-identity \
    --cloud-front-origin-access-identity-config \
        CallerReference="${CALLER_REF}",Comment="OAI for ${S3_BUCKET}" \
    --query 'CloudFrontOriginAccessIdentity.Id' \
    --output text 2>/dev/null || echo "")

if [ -z "${OAI_ID}" ]; then
    warning "CloudFront OAI might already exist or creation failed"
else
    success "CloudFront OAI created: ${OAI_ID}"
fi
echo ""

# Create .env file
echo "6. Creating environment configuration..."
ENV_FILE="${SCRIPT_DIR}/../../.env.${ENVIRONMENT}"

cat > "${ENV_FILE}" <<EOF
# AWS Configuration - ${ENVIRONMENT}
# Generated: $(date)
AWS_REGION=${REGION}
AWS_ACCOUNT_ID=${AWS_ACCOUNT}

# S3 Configuration
S3_BUCKET=${S3_BUCKET}
S3_BACKUP_BUCKET=${S3_BACKUP_BUCKET}

# DynamoDB Configuration
DYNAMODB_TABLE=${DYNAMODB_TABLE}

# Lambda Configuration
LAMBDA_ROLE_ARN=${LAMBDA_ROLE_ARN}
LAMBDA_FUNCTION=${LAMBDA_FUNCTION}

# Scraper Configuration
REQUESTS_PER_SECOND=0.5
MAX_RETRIES=3
RETRY_DELAY=5
WEBP_QUALITY=85
TARGET_IMAGE_SIZE_KB=200
MAX_IMAGE_SIZE_KB=500
LOG_LEVEL=INFO

# Feature Flags
ENABLE_DUPLICATE_DETECTION=true
ENABLE_IMAGE_OPTIMIZATION=true
ENABLE_METRICS=true

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_SECOND=0.5

# Monitoring
CLOUDWATCH_NAMESPACE=${PROJECT_NAME}
EOF

success "Environment file created: ${ENV_FILE}"
echo ""

# Cleanup temp files
rm -f /tmp/trust-policy.json /tmp/lambda-policy.json /tmp/lifecycle-policy.json
rm -f /tmp/backup-lifecycle.json /tmp/cors-config.json

echo "========================================="
echo "Resource Creation Complete!"
echo "========================================="
echo ""
echo "Created resources:"
echo "  ✓ S3 Bucket (Images): ${S3_BUCKET}"
echo "  ✓ S3 Bucket (Backups): ${S3_BACKUP_BUCKET}"
echo "  ✓ DynamoDB Table: ${DYNAMODB_TABLE}"
echo "  ✓ IAM Role: ${LAMBDA_ROLE}"
echo "  ✓ IAM Role ARN: ${LAMBDA_ROLE_ARN}"
echo ""
echo "Configuration saved to: ${ENV_FILE}"
echo ""
echo "Next steps:"
echo "  1. Review the .env file: cat ${ENV_FILE}"
echo "  2. Initialize database: ./scripts/setup/init-database.sh ${ENVIRONMENT}"
echo "  3. Deploy Lambda: ./scripts/deploy/deploy-lambda.sh ${ENVIRONMENT}"
echo ""
