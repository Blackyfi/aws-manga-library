#!/bin/bash
###############################################################################
# Database Initialization Script
# ================================
#
# Initializes DynamoDB tables with required structure and seed data
# Creates indexes, sets up initial data, and validates the setup
#
# Usage: ./init-database.sh [environment]
# Example: ./init-database.sh dev
###############################################################################

set -e  # Exit on error

# Configuration
ENVIRONMENT="${1:-dev}"
PROJECT_NAME="manga-scraper"
REGION="${AWS_REGION:-eu-west-3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load environment variables
ENV_FILE="${SCRIPT_DIR}/../../.env.${ENVIRONMENT}"
if [ -f "${ENV_FILE}" ]; then
    source "${ENV_FILE}"
else
    echo "Error: Environment file not found: ${ENV_FILE}"
    echo "Please run ./scripts/setup/create-aws-resources.sh first"
    exit 1
fi

echo "========================================="
echo "Database Initialization"
echo "========================================="
echo "Environment: ${ENVIRONMENT}"
echo "Region: ${REGION}"
echo "Table: ${DYNAMODB_TABLE}"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

# Check if table exists
echo "1. Verifying DynamoDB table..."
if ! aws dynamodb describe-table --table-name "${DYNAMODB_TABLE}" --region "${REGION}" &> /dev/null; then
    error "Table ${DYNAMODB_TABLE} does not exist"
    echo "Please run: ./scripts/setup/create-aws-resources.sh ${ENVIRONMENT}"
    exit 1
fi
success "Table exists"
echo ""

# Function to put item in DynamoDB
put_item() {
    local item="$1"
    aws dynamodb put-item \
        --table-name "${DYNAMODB_TABLE}" \
        --item "${item}" \
        --region "${REGION}" \
        --return-consumed-capacity TOTAL > /dev/null
}

# Initialize metadata
echo "2. Creating system metadata..."

# System configuration item
SYSTEM_CONFIG=$(cat <<EOF
{
    "PK": {"S": "SYSTEM#CONFIG"},
    "SK": {"S": "v1"},
    "EntityType": {"S": "SystemConfig"},
    "Version": {"S": "1.0.0"},
    "CreatedAt": {"S": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"},
    "UpdatedAt": {"S": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"},
    "Settings": {"M": {
        "RateLimit": {"N": "0.5"},
        "MaxRetries": {"N": "3"},
        "ImageQuality": {"N": "85"},
        "EnableDuplicateDetection": {"BOOL": true}
    }}
}
EOF
)

put_item "${SYSTEM_CONFIG}"
success "System configuration created"

# Statistics item
STATS_CONFIG=$(cat <<EOF
{
    "PK": {"S": "STATS#GLOBAL"},
    "SK": {"S": "CURRENT"},
    "EntityType": {"S": "Statistics"},
    "TotalManga": {"N": "0"},
    "TotalChapters": {"N": "0"},
    "TotalImages": {"N": "0"},
    "TotalSizeBytes": {"N": "0"},
    "LastUpdated": {"S": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"},
    "GSI1PK": {"S": "STATS"},
    "GSI1SK": {"S": "GLOBAL"}
}
EOF
)

put_item "${STATS_CONFIG}"
success "Statistics initialized"
echo ""

# Create sample manga sources
echo "3. Creating manga sources..."

# MangaDex source
MANGADEX_SOURCE=$(cat <<EOF
{
    "PK": {"S": "SOURCE#mangadex"},
    "SK": {"S": "CONFIG"},
    "EntityType": {"S": "Source"},
    "SourceId": {"S": "mangadex"},
    "Name": {"S": "MangaDex"},
    "BaseUrl": {"S": "https://mangadex.org"},
    "ApiUrl": {"S": "https://api.mangadex.org"},
    "Enabled": {"BOOL": true},
    "RateLimit": {"N": "0.5"},
    "Priority": {"N": "1"},
    "Features": {"L": [
        {"S": "api"},
        {"S": "bulk_download"},
        {"S": "metadata"}
    ]},
    "CreatedAt": {"S": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"},
    "GSI1PK": {"S": "SOURCES"},
    "GSI1SK": {"S": "mangadex"}
}
EOF
)

put_item "${MANGADEX_SOURCE}"
success "MangaDex source created"

# MangaKakalot source
MANGAKAKALOT_SOURCE=$(cat <<EOF
{
    "PK": {"S": "SOURCE#mangakakalot"},
    "SK": {"S": "CONFIG"},
    "EntityType": {"S": "Source"},
    "SourceId": {"S": "mangakakalot"},
    "Name": {"S": "MangaKakalot"},
    "BaseUrl": {"S": "https://mangakakalot.com"},
    "Enabled": {"BOOL": true},
    "RateLimit": {"N": "1.0"},
    "Priority": {"N": "2"},
    "Features": {"L": [
        {"S": "web_scraping"},
        {"S": "popular_manga"}
    ]},
    "CreatedAt": {"S": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"},
    "GSI1PK": {"S": "SOURCES"},
    "GSI1SK": {"S": "mangakakalot"}
}
EOF
)

put_item "${MANGAKAKALOT_SOURCE}"
success "MangaKakalot source created"
echo ""

# Create sample categories
echo "4. Creating manga categories..."

CATEGORIES=("Action" "Adventure" "Comedy" "Drama" "Fantasy" "Horror" "Mystery" "Romance" "Sci-Fi" "Slice of Life")

for category in "${CATEGORIES[@]}"; do
    CATEGORY_ITEM=$(cat <<EOF
{
    "PK": {"S": "CATEGORY#$(echo ${category} | tr '[:upper:]' '[:lower:]' | tr ' ' '-')"},
    "SK": {"S": "META"},
    "EntityType": {"S": "Category"},
    "Name": {"S": "${category}"},
    "Slug": {"S": "$(echo ${category} | tr '[:upper:]' '[:lower:]' | tr ' ' '-')"},
    "MangaCount": {"N": "0"},
    "CreatedAt": {"S": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"},
    "GSI1PK": {"S": "CATEGORIES"},
    "GSI1SK": {"S": "$(echo ${category} | tr '[:upper:]' '[:lower:]' | tr ' ' '-')"}
}
EOF
)
    put_item "${CATEGORY_ITEM}"
done

success "Created ${#CATEGORIES[@]} categories"
echo ""

# Create job queue metadata
echo "5. Creating job queue metadata..."

JOB_QUEUE=$(cat <<EOF
{
    "PK": {"S": "QUEUE#SCRAPER"},
    "SK": {"S": "STATUS"},
    "EntityType": {"S": "Queue"},
    "QueueName": {"S": "scraper"},
    "Status": {"S": "idle"},
    "PendingJobs": {"N": "0"},
    "ProcessingJobs": {"N": "0"},
    "CompletedJobs": {"N": "0"},
    "FailedJobs": {"N": "0"},
    "LastProcessed": {"S": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"},
    "GSI1PK": {"S": "QUEUES"},
    "GSI1SK": {"S": "scraper"}
}
EOF
)

put_item "${JOB_QUEUE}"
success "Job queue metadata created"
echo ""

# Verify initialization
echo "6. Verifying database initialization..."

# Count items
ITEM_COUNT=$(aws dynamodb scan \
    --table-name "${DYNAMODB_TABLE}" \
    --select "COUNT" \
    --region "${REGION}" \
    --query 'Count' \
    --output text)

success "Database contains ${ITEM_COUNT} items"

# Verify key items exist
echo "  Checking required items..."

check_item() {
    local pk="$1"
    local sk="$2"
    if aws dynamodb get-item \
        --table-name "${DYNAMODB_TABLE}" \
        --key "{\"PK\": {\"S\": \"${pk}\"}, \"SK\": {\"S\": \"${sk}\"}}" \
        --region "${REGION}" \
        --output text > /dev/null 2>&1; then
        echo "    ✓ ${pk}/${sk}"
    else
        warning "Missing: ${pk}/${sk}"
    fi
}

check_item "SYSTEM#CONFIG" "v1"
check_item "STATS#GLOBAL" "CURRENT"
check_item "SOURCE#mangadex" "CONFIG"
check_item "SOURCE#mangakakalot" "CONFIG"
check_item "QUEUE#SCRAPER" "STATUS"

echo ""

# Create indexes info file
echo "7. Creating database documentation..."

DOC_FILE="${SCRIPT_DIR}/../../docs/database-schema.md"
mkdir -p "$(dirname ${DOC_FILE})"

cat > "${DOC_FILE}" <<'EOF'
# Database Schema Documentation

## DynamoDB Table Structure

### Primary Key Design
- **PK (Partition Key)**: Entity type and ID (e.g., `MANGA#one-piece`, `SOURCE#mangadex`)
- **SK (Sort Key)**: Sub-entity or version (e.g., `META`, `CHAPTER#1`, `v1`)

### Global Secondary Index (GSI1)
- **GSI1PK**: Entity type for querying (e.g., `MANGA`, `SOURCES`, `STATS`)
- **GSI1SK**: Sortable attribute (e.g., timestamp, name, slug)

## Entity Types

### System Configuration
```
PK: SYSTEM#CONFIG
SK: v1
```
Stores global system settings and configuration.

### Statistics
```
PK: STATS#GLOBAL
SK: CURRENT
GSI1PK: STATS
GSI1SK: GLOBAL
```
Tracks overall system statistics.

### Manga Source
```
PK: SOURCE#{source_id}
SK: CONFIG
GSI1PK: SOURCES
GSI1SK: {source_id}
```
Configuration for manga scraping sources.

### Manga
```
PK: MANGA#{manga_id}
SK: META
GSI1PK: MANGA
GSI1SK: {created_at}
```
Manga metadata and information.

### Chapter
```
PK: MANGA#{manga_id}
SK: CHAPTER#{chapter_number}
GSI1PK: CHAPTERS
GSI1SK: {manga_id}#{chapter_number}
```
Chapter information for a specific manga.

### Category
```
PK: CATEGORY#{category_slug}
SK: META
GSI1PK: CATEGORIES
GSI1SK: {category_slug}
```
Manga categories/genres.

### Job Queue
```
PK: QUEUE#{queue_name}
SK: STATUS
GSI1PK: QUEUES
GSI1SK: {queue_name}
```
Job queue status and metrics.

### Job
```
PK: JOB#{job_id}
SK: STATUS
GSI1PK: JOBS
GSI1SK: {created_at}
```
Individual scraping job information.

## Query Patterns

1. **Get manga by ID**: Query with `PK = MANGA#{id}` and `SK = META`
2. **List all manga**: Query GSI1 with `GSI1PK = MANGA`
3. **Get manga chapters**: Query with `PK = MANGA#{id}` and `SK begins_with CHAPTER#`
4. **List sources**: Query GSI1 with `GSI1PK = SOURCES`
5. **Get statistics**: Query with `PK = STATS#GLOBAL` and `SK = CURRENT`

## Initialization Date
EOF

echo "Initialized: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${DOC_FILE}"
echo "Environment: ${ENVIRONMENT}" >> "${DOC_FILE}"
echo "Table: ${DYNAMODB_TABLE}" >> "${DOC_FILE}"

success "Documentation created: ${DOC_FILE}"
echo ""

echo "========================================="
echo "Database Initialization Complete!"
echo "========================================="
echo ""
echo "Summary:"
echo "  ✓ System configuration initialized"
echo "  ✓ Statistics tracking enabled"
echo "  ✓ ${#CATEGORIES[@]} categories created"
echo "  ✓ 2 manga sources configured"
echo "  ✓ Job queue initialized"
echo "  ✓ Total items: ${ITEM_COUNT}"
echo ""
echo "Database is ready for use!"
echo ""
echo "Next steps:"
echo "  1. Deploy Lambda function: ./scripts/deploy/deploy-lambda.sh ${ENVIRONMENT}"
echo "  2. Test scraper: cd scraper && python scripts/example_usage.py"
echo "  3. View documentation: cat ${DOC_FILE}"
echo ""
