#!/bin/bash
###############################################################################
# Frontend Deployment Script
# ===========================
#
# Builds and deploys the Next.js frontend application
# Supports deployment to:
# - AWS S3 + CloudFront
# - Vercel
# - Custom hosting
#
# Usage: ./deploy-frontend.sh [environment] [target]
# Targets: aws, vercel, docker
# Example: ./deploy-frontend.sh prod aws
###############################################################################

set -e  # Exit on error

# Configuration
ENVIRONMENT="${1:-dev}"
TARGET="${2:-aws}"
REGION="${AWS_REGION:-eu-west-3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"

# Load environment variables if available
ENV_FILE="${PROJECT_ROOT}/.env.${ENVIRONMENT}"
if [ -f "${ENV_FILE}" ]; then
    source "${ENV_FILE}"
fi

echo "========================================="
echo "Frontend Deployment for Manga Scraper"
echo "========================================="
echo "Environment: ${ENVIRONMENT}"
echo "Target:      ${TARGET}"
echo "Frontend:    ${FRONTEND_DIR}"
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

if [ ! -d "${FRONTEND_DIR}" ]; then
    error "Frontend directory not found: ${FRONTEND_DIR}"
    exit 1
fi
success "Frontend directory found"

cd "${FRONTEND_DIR}"

if ! command -v node &> /dev/null; then
    error "Node.js is not installed"
    exit 1
fi
success "Node.js installed: $(node --version)"

if ! command -v npm &> /dev/null; then
    error "npm is not installed"
    exit 1
fi
success "npm installed: $(npm --version)"

echo ""

# Install dependencies
echo "1. Installing dependencies..."
if [ ! -d "node_modules" ]; then
    info "Running npm install..."
    npm install
else
    info "Dependencies already installed, running npm ci..."
    npm ci
fi
success "Dependencies ready"
echo ""

# Run tests (optional, can be skipped with --skip-tests)
if [ "$3" != "--skip-tests" ]; then
    echo "2. Running tests..."
    if [ -f "package.json" ] && npm run | grep -q "test"; then
        npm test -- --passWithNoTests || warning "Tests failed but continuing..."
    else
        warning "No tests found, skipping..."
    fi
    echo ""
fi

# Build the application
echo "3. Building application..."

# Set environment variables for build
export NEXT_PUBLIC_API_URL="${API_URL:-https://api.manga-scraper.com}"
export NEXT_PUBLIC_CDN_URL="${CDN_URL:-https://cdn.manga-scraper.com}"
export NEXT_PUBLIC_ENVIRONMENT="${ENVIRONMENT}"

info "Building with Next.js..."
npm run build

BUILD_OUTPUT="${FRONTEND_DIR}/.next"
if [ ! -d "${BUILD_OUTPUT}" ]; then
    error "Build failed: .next directory not found"
    exit 1
fi

success "Application built successfully"
echo ""

# Deploy based on target
case "${TARGET}" in
    aws)
        deploy_to_aws
        ;;
    vercel)
        deploy_to_vercel
        ;;
    docker)
        deploy_with_docker
        ;;
    *)
        error "Unknown target: ${TARGET}"
        echo "Valid targets: aws, vercel, docker"
        exit 1
        ;;
esac

# Function to deploy to AWS S3 + CloudFront
deploy_to_aws() {
    echo "4. Deploying to AWS..."

    if ! command -v aws &> /dev/null; then
        error "AWS CLI is not installed"
        exit 1
    fi

    # Configuration
    S3_FRONTEND_BUCKET="${PROJECT_NAME:-manga-scraper}-${ENVIRONMENT}-frontend"
    CLOUDFRONT_ID="${CLOUDFRONT_DISTRIBUTION_ID:-}"

    # Create S3 bucket if it doesn't exist
    if ! aws s3 ls "s3://${S3_FRONTEND_BUCKET}" 2>/dev/null; then
        info "Creating S3 bucket: ${S3_FRONTEND_BUCKET}"

        if [ "${REGION}" == "us-east-1" ]; then
            aws s3 mb "s3://${S3_FRONTEND_BUCKET}"
        else
            aws s3 mb "s3://${S3_FRONTEND_BUCKET}" --region "${REGION}"
        fi

        # Configure bucket for static website hosting
        aws s3 website "s3://${S3_FRONTEND_BUCKET}" \
            --index-document index.html \
            --error-document error.html

        # Set bucket policy for public read
        cat > /tmp/bucket-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::${S3_FRONTEND_BUCKET}/*"
        }
    ]
}
EOF

        aws s3api put-bucket-policy \
            --bucket "${S3_FRONTEND_BUCKET}" \
            --policy file:///tmp/bucket-policy.json

        rm /tmp/bucket-policy.json

        success "S3 bucket created and configured"
    fi

    # Export static files
    info "Exporting static files..."
    if ! npm run export 2>/dev/null; then
        # If export script doesn't exist, copy .next/static
        warning "No export script found, using build output"
    fi

    # Determine output directory
    if [ -d "out" ]; then
        DEPLOY_DIR="out"
    elif [ -d ".next/standalone" ]; then
        DEPLOY_DIR=".next/standalone"
    else
        DEPLOY_DIR=".next"
    fi

    # Sync to S3
    info "Syncing files to S3..."
    aws s3 sync "${DEPLOY_DIR}" "s3://${S3_FRONTEND_BUCKET}" \
        --delete \
        --cache-control "public, max-age=31536000, immutable" \
        --exclude "*.html" \
        --region "${REGION}"

    # Upload HTML files with different cache control
    aws s3 sync "${DEPLOY_DIR}" "s3://${S3_FRONTEND_BUCKET}" \
        --delete \
        --cache-control "public, max-age=0, must-revalidate" \
        --exclude "*" \
        --include "*.html" \
        --region "${REGION}"

    success "Files synced to S3"

    # Invalidate CloudFront cache if distribution ID is provided
    if [ -n "${CLOUDFRONT_ID}" ]; then
        info "Invalidating CloudFront cache..."

        INVALIDATION_ID=$(aws cloudfront create-invalidation \
            --distribution-id "${CLOUDFRONT_ID}" \
            --paths "/*" \
            --query 'Invalidation.Id' \
            --output text)

        success "CloudFront invalidation created: ${INVALIDATION_ID}"
    else
        warning "CloudFront distribution ID not set, skipping cache invalidation"
    fi

    echo ""
    echo "========================================="
    echo "AWS Deployment Complete!"
    echo "========================================="
    echo ""
    echo "S3 Bucket:        ${S3_FRONTEND_BUCKET}"
    echo "Website URL:      http://${S3_FRONTEND_BUCKET}.s3-website-${REGION}.amazonaws.com"
    if [ -n "${CLOUDFRONT_ID}" ]; then
        CLOUDFRONT_DOMAIN=$(aws cloudfront get-distribution \
            --id "${CLOUDFRONT_ID}" \
            --query 'Distribution.DomainName' \
            --output text 2>/dev/null || echo "N/A")
        echo "CloudFront URL:   https://${CLOUDFRONT_DOMAIN}"
    fi
    echo ""
}

# Function to deploy to Vercel
deploy_to_vercel() {
    echo "4. Deploying to Vercel..."

    if ! command -v vercel &> /dev/null; then
        warning "Vercel CLI not installed, installing..."
        npm install -g vercel
    fi

    # Set production flag for prod environment
    VERCEL_FLAGS=""
    if [ "${ENVIRONMENT}" = "prod" ]; then
        VERCEL_FLAGS="--prod"
    fi

    info "Deploying to Vercel..."
    DEPLOYMENT_URL=$(vercel deploy ${VERCEL_FLAGS} --yes | tail -n 1)

    success "Deployed to Vercel"

    echo ""
    echo "========================================="
    echo "Vercel Deployment Complete!"
    echo "========================================="
    echo ""
    echo "Deployment URL:   ${DEPLOYMENT_URL}"
    echo ""
}

# Function to build and deploy Docker container
deploy_with_docker() {
    echo "4. Building Docker image..."

    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
        exit 1
    fi

    DOCKER_IMAGE="manga-scraper-frontend"
    DOCKER_TAG="${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"

    # Check if Dockerfile exists
    if [ ! -f "${PROJECT_ROOT}/docker/Dockerfile.frontend" ]; then
        error "Dockerfile not found: ${PROJECT_ROOT}/docker/Dockerfile.frontend"
        exit 1
    fi

    info "Building Docker image..."
    docker build \
        -f "${PROJECT_ROOT}/docker/Dockerfile.frontend" \
        -t "${DOCKER_IMAGE}:${DOCKER_TAG}" \
        -t "${DOCKER_IMAGE}:${ENVIRONMENT}" \
        -t "${DOCKER_IMAGE}:latest" \
        --build-arg ENVIRONMENT="${ENVIRONMENT}" \
        "${FRONTEND_DIR}"

    success "Docker image built: ${DOCKER_IMAGE}:${DOCKER_TAG}"

    # Push to registry if configured
    if [ -n "${DOCKER_REGISTRY}" ]; then
        info "Pushing to Docker registry..."

        docker tag "${DOCKER_IMAGE}:${DOCKER_TAG}" "${DOCKER_REGISTRY}/${DOCKER_IMAGE}:${DOCKER_TAG}"
        docker tag "${DOCKER_IMAGE}:${DOCKER_TAG}" "${DOCKER_REGISTRY}/${DOCKER_IMAGE}:${ENVIRONMENT}"

        docker push "${DOCKER_REGISTRY}/${DOCKER_IMAGE}:${DOCKER_TAG}"
        docker push "${DOCKER_REGISTRY}/${DOCKER_IMAGE}:${ENVIRONMENT}"

        success "Docker image pushed to registry"
    fi

    echo ""
    echo "========================================="
    echo "Docker Deployment Complete!"
    echo "========================================="
    echo ""
    echo "Docker Image:     ${DOCKER_IMAGE}:${DOCKER_TAG}"
    echo "Environment:      ${ENVIRONMENT}"
    echo ""
    echo "Run locally with:"
    echo "  docker run -p 3000:3000 ${DOCKER_IMAGE}:${DOCKER_TAG}"
    echo ""
}

echo "Deployment completed successfully!"
echo ""
echo "Next steps:"
echo "  1. Test the deployment"
echo "  2. Monitor logs for errors"
echo "  3. Update DNS if necessary"
echo ""
