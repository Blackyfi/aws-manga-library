#!/bin/bash
###############################################################################
# Generate Usage Report Script
# ==============================
#
# Generates comprehensive usage and statistics reports
# Includes:
# - System metrics
# - Cost analysis
# - Usage statistics
# - Performance metrics
#
# Usage: ./generate-report.sh [environment] [report-type] [period]
# Report types: usage, cost, performance, full
# Periods: daily, weekly, monthly
# Example: ./generate-report.sh prod full monthly
###############################################################################

set -e  # Exit on error

# Configuration
ENVIRONMENT="${1:-dev}"
REPORT_TYPE="${2:-usage}"
PERIOD="${3:-daily}"
REGION="${AWS_REGION:-eu-west-3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Load environment variables
ENV_FILE="${PROJECT_ROOT}/.env.${ENVIRONMENT}"
if [ -f "${ENV_FILE}" ]; then
    source "${ENV_FILE}"
fi

FUNCTION_NAME="${LAMBDA_FUNCTION:-manga-scraper-${ENVIRONMENT}}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

echo "========================================="
echo "Generate Usage Report"
echo "========================================="
echo "Environment:  ${ENVIRONMENT}"
echo "Report Type:  ${REPORT_TYPE}"
echo "Period:       ${PERIOD}"
echo "Time:         $(date)"
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

# Calculate time range based on period
case "${PERIOD}" in
    daily)
        START_TIME=$(date -u -d "1 day ago" +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -u -v-1d +%Y-%m-%dT%H:%M:%S)
        ;;
    weekly)
        START_TIME=$(date -u -d "7 days ago" +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -u -v-7d +%Y-%m-%dT%H:%M:%S)
        ;;
    monthly)
        START_TIME=$(date -u -d "30 days ago" +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -u -v-30d +%Y-%m-%dT%H:%M:%S)
        ;;
    *)
        error "Unknown period: ${PERIOD}"
        exit 1
        ;;
esac

END_TIME=$(date -u +%Y-%m-%dT%H:%M:%S)
START_TIMESTAMP=$(date -d "${START_TIME}" +%s 2>/dev/null || date -j -f %Y-%m-%dT%H:%M:%S "${START_TIME}" +%s)
END_TIMESTAMP=$(date -d "${END_TIME}" +%s 2>/dev/null || date -j -f %Y-%m-%dT%H:%M:%S "${END_TIME}" +%s)

info "Report period: ${START_TIME} to ${END_TIME}"
echo ""

# Create report directory
REPORT_DIR="${PROJECT_ROOT}/.reports/${ENVIRONMENT}"
mkdir -p "${REPORT_DIR}"

# Function to generate usage statistics
generate_usage_report() {
    echo "========================================="
    echo "Usage Statistics"
    echo "========================================="
    echo ""

    # Lambda invocations
    if [ -n "${FUNCTION_NAME}" ]; then
        info "Lambda Function: ${FUNCTION_NAME}"

        INVOCATIONS=$(aws cloudwatch get-metric-statistics \
            --namespace AWS/Lambda \
            --metric-name Invocations \
            --dimensions Name=FunctionName,Value=${FUNCTION_NAME} \
            --start-time "${START_TIME}" \
            --end-time "${END_TIME}" \
            --period 3600 \
            --statistics Sum \
            --region "${REGION}" \
            --query 'Datapoints[].Sum' \
            --output json 2>/dev/null | jq 'add // 0' || echo "0")

        ERRORS=$(aws cloudwatch get-metric-statistics \
            --namespace AWS/Lambda \
            --metric-name Errors \
            --dimensions Name=FunctionName,Value=${FUNCTION_NAME} \
            --start-time "${START_TIME}" \
            --end-time "${END_TIME}" \
            --period 3600 \
            --statistics Sum \
            --region "${REGION}" \
            --query 'Datapoints[].Sum' \
            --output json 2>/dev/null | jq 'add // 0' || echo "0")

        THROTTLES=$(aws cloudwatch get-metric-statistics \
            --namespace AWS/Lambda \
            --metric-name Throttles \
            --dimensions Name=FunctionName,Value=${FUNCTION_NAME} \
            --start-time "${START_TIME}" \
            --end-time "${END_TIME}" \
            --period 3600 \
            --statistics Sum \
            --region "${REGION}" \
            --query 'Datapoints[].Sum' \
            --output json 2>/dev/null | jq 'add // 0' || echo "0")

        AVG_DURATION=$(aws cloudwatch get-metric-statistics \
            --namespace AWS/Lambda \
            --metric-name Duration \
            --dimensions Name=FunctionName,Value=${FUNCTION_NAME} \
            --start-time "${START_TIME}" \
            --end-time "${END_TIME}" \
            --period 3600 \
            --statistics Average \
            --region "${REGION}" \
            --query 'Datapoints[].Average' \
            --output json 2>/dev/null | jq 'add / length // 0' || echo "0")

        echo "  Invocations:     ${INVOCATIONS}"
        echo "  Errors:          ${ERRORS}"
        echo "  Throttles:       ${THROTTLES}"
        echo "  Avg Duration:    ${AVG_DURATION} ms"

        if [ "${INVOCATIONS}" -gt 0 ]; then
            ERROR_RATE=$(echo "scale=2; ${ERRORS} * 100 / ${INVOCATIONS}" | bc)
            echo "  Error Rate:      ${ERROR_RATE}%"
        fi

        echo ""
    fi

    # S3 statistics
    if [ -n "${S3_BUCKET}" ]; then
        info "S3 Bucket: ${S3_BUCKET}"

        BUCKET_SIZE=$(aws s3 ls "s3://${S3_BUCKET}" --recursive --summarize 2>/dev/null | grep "Total Size" | awk '{print $3}')
        OBJECT_COUNT=$(aws s3 ls "s3://${S3_BUCKET}" --recursive --summarize 2>/dev/null | grep "Total Objects" | awk '{print $3}')

        BUCKET_SIZE_GB=$(echo "scale=2; ${BUCKET_SIZE} / 1024 / 1024 / 1024" | bc)

        echo "  Object Count:    ${OBJECT_COUNT}"
        echo "  Total Size:      ${BUCKET_SIZE_GB} GB"
        echo ""
    fi

    # DynamoDB statistics
    if [ -n "${DYNAMODB_TABLE}" ]; then
        info "DynamoDB Table: ${DYNAMODB_TABLE}"

        ITEM_COUNT=$(aws dynamodb describe-table \
            --table-name "${DYNAMODB_TABLE}" \
            --region "${REGION}" \
            --query 'Table.ItemCount' \
            --output text)

        TABLE_SIZE=$(aws dynamodb describe-table \
            --table-name "${DYNAMODB_TABLE}" \
            --region "${REGION}" \
            --query 'Table.TableSizeBytes' \
            --output text)

        TABLE_SIZE_MB=$(echo "scale=2; ${TABLE_SIZE} / 1024 / 1024" | bc)

        # Get statistics from DynamoDB
        STATS=$(aws dynamodb get-item \
            --table-name "${DYNAMODB_TABLE}" \
            --key '{"PK":{"S":"STATS#GLOBAL"},"SK":{"S":"CURRENT"}}' \
            --region "${REGION}" \
            --output json 2>/dev/null || echo '{}')

        TOTAL_MANGA=$(echo "${STATS}" | jq -r '.Item.TotalManga.N // "0"')
        TOTAL_CHAPTERS=$(echo "${STATS}" | jq -r '.Item.TotalChapters.N // "0"')
        TOTAL_IMAGES=$(echo "${STATS}" | jq -r '.Item.TotalImages.N // "0"')

        echo "  Total Items:     ${ITEM_COUNT}"
        echo "  Table Size:      ${TABLE_SIZE_MB} MB"
        echo "  Total Manga:     ${TOTAL_MANGA}"
        echo "  Total Chapters:  ${TOTAL_CHAPTERS}"
        echo "  Total Images:    ${TOTAL_IMAGES}"
        echo ""
    fi
}

# Function to generate cost analysis
generate_cost_report() {
    echo "========================================="
    echo "Cost Analysis"
    echo "========================================="
    echo ""

    info "Analyzing costs for ${PERIOD} period..."

    # Get cost and usage data
    COST_DATA=$(aws ce get-cost-and-usage \
        --time-period Start=${START_TIME:0:10},End=${END_TIME:0:10} \
        --granularity DAILY \
        --metrics "UnblendedCost" \
        --filter file://<(cat <<EOF
{
    "Tags": {
        "Key": "Environment",
        "Values": ["${ENVIRONMENT}"]
    }
}
EOF
) \
        --region us-east-1 \
        --output json 2>/dev/null || echo '{"ResultsByTime":[]}')

    TOTAL_COST=$(echo "${COST_DATA}" | jq -r '[.ResultsByTime[].Total.UnblendedCost.Amount | tonumber] | add // 0')

    echo "  Total Cost:      \$${TOTAL_COST}"

    # Breakdown by service
    SERVICE_COSTS=$(aws ce get-cost-and-usage \
        --time-period Start=${START_TIME:0:10},End=${END_TIME:0:10} \
        --granularity MONTHLY \
        --metrics "UnblendedCost" \
        --group-by Type=DIMENSION,Key=SERVICE \
        --filter file://<(cat <<EOF
{
    "Tags": {
        "Key": "Environment",
        "Values": ["${ENVIRONMENT}"]
    }
}
EOF
) \
        --region us-east-1 \
        --output json 2>/dev/null || echo '{"ResultsByTime":[]}')

    echo ""
    echo "  Cost by Service:"
    echo "${SERVICE_COSTS}" | jq -r '.ResultsByTime[].Groups[] | "    \(.Keys[0]): $\(.Metrics.UnblendedCost.Amount)"' 2>/dev/null || echo "    N/A"

    echo ""
}

# Function to generate performance metrics
generate_performance_report() {
    echo "========================================="
    echo "Performance Metrics"
    echo "========================================="
    echo ""

    if [ -n "${FUNCTION_NAME}" ]; then
        info "Lambda Performance"

        # Get CloudWatch metrics
        DURATION_STATS=$(aws cloudwatch get-metric-statistics \
            --namespace AWS/Lambda \
            --metric-name Duration \
            --dimensions Name=FunctionName,Value=${FUNCTION_NAME} \
            --start-time "${START_TIME}" \
            --end-time "${END_TIME}" \
            --period 3600 \
            --statistics Average,Maximum,Minimum \
            --region "${REGION}" \
            --output json 2>/dev/null)

        AVG_DURATION=$(echo "${DURATION_STATS}" | jq -r '[.Datapoints[].Average] | add / length // 0')
        MAX_DURATION=$(echo "${DURATION_STATS}" | jq -r '[.Datapoints[].Maximum] | max // 0')
        MIN_DURATION=$(echo "${DURATION_STATS}" | jq -r '[.Datapoints[].Minimum] | min // 0')

        echo "  Duration (ms):"
        echo "    Average:       ${AVG_DURATION}"
        echo "    Maximum:       ${MAX_DURATION}"
        echo "    Minimum:       ${MIN_DURATION}"

        # Memory utilization
        MEMORY_STATS=$(aws cloudwatch get-metric-statistics \
            --namespace AWS/Lambda \
            --metric-name MemoryUtilization \
            --dimensions Name=FunctionName,Value=${FUNCTION_NAME} \
            --start-time "${START_TIME}" \
            --end-time "${END_TIME}" \
            --period 3600 \
            --statistics Average,Maximum \
            --region "${REGION}" \
            --output json 2>/dev/null || echo '{"Datapoints":[]}')

        AVG_MEMORY=$(echo "${MEMORY_STATS}" | jq -r '[.Datapoints[].Average] | add / length // 0')
        MAX_MEMORY=$(echo "${MEMORY_STATS}" | jq -r '[.Datapoints[].Maximum] | max // 0')

        echo ""
        echo "  Memory Utilization (%):"
        echo "    Average:       ${AVG_MEMORY}"
        echo "    Maximum:       ${MAX_MEMORY}"

        echo ""
    fi

    # API response times (if API Gateway is used)
    info "API Performance"
    echo "  (Metrics would show API latency, request counts, etc.)"
    echo ""
}

# Generate report based on type
case "${REPORT_TYPE}" in
    usage)
        generate_usage_report
        ;;
    cost)
        generate_cost_report
        ;;
    performance)
        generate_performance_report
        ;;
    full)
        generate_usage_report
        generate_cost_report
        generate_performance_report
        ;;
    *)
        error "Unknown report type: ${REPORT_TYPE}"
        echo "Valid types: usage, cost, performance, full"
        exit 1
        ;;
esac

# Generate JSON report
JSON_REPORT="${REPORT_DIR}/report-${REPORT_TYPE}-${PERIOD}-${TIMESTAMP}.json"

cat > "${JSON_REPORT}" <<EOF
{
    "report_type": "${REPORT_TYPE}",
    "environment": "${ENVIRONMENT}",
    "period": "${PERIOD}",
    "generated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "time_range": {
        "start": "${START_TIME}",
        "end": "${END_TIME}"
    },
    "lambda": {
        "function_name": "${FUNCTION_NAME}",
        "invocations": ${INVOCATIONS:-0},
        "errors": ${ERRORS:-0},
        "throttles": ${THROTTLES:-0},
        "avg_duration_ms": ${AVG_DURATION:-0}
    },
    "s3": {
        "bucket": "${S3_BUCKET}",
        "object_count": ${OBJECT_COUNT:-0},
        "size_bytes": ${BUCKET_SIZE:-0}
    },
    "dynamodb": {
        "table": "${DYNAMODB_TABLE}",
        "item_count": ${ITEM_COUNT:-0},
        "size_bytes": ${TABLE_SIZE:-0},
        "total_manga": ${TOTAL_MANGA:-0},
        "total_chapters": ${TOTAL_CHAPTERS:-0},
        "total_images": ${TOTAL_IMAGES:-0}
    },
    "cost": {
        "total": ${TOTAL_COST:-0}
    }
}
EOF

success "JSON report saved: ${JSON_REPORT}"

# Generate HTML report
HTML_REPORT="${REPORT_DIR}/report-${REPORT_TYPE}-${PERIOD}-${TIMESTAMP}.html"

cat > "${HTML_REPORT}" <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Manga Scraper Report - ${ENVIRONMENT}</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .header h1 {
            margin: 0;
            font-size: 2em;
        }
        .metadata {
            opacity: 0.9;
            margin-top: 10px;
        }
        .section {
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .section h2 {
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-top: 0;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        .metric:last-child {
            border-bottom: none;
        }
        .metric-label {
            font-weight: 600;
            color: #555;
        }
        .metric-value {
            color: #333;
            font-size: 1.1em;
        }
        .footer {
            text-align: center;
            color: #777;
            margin-top: 30px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Manga Scraper - ${REPORT_TYPE^} Report</h1>
        <div class="metadata">
            <p>Environment: <strong>${ENVIRONMENT}</strong> | Period: <strong>${PERIOD}</strong></p>
            <p>Generated: $(date)</p>
        </div>
    </div>

    <div class="section">
        <h2>Lambda Function</h2>
        <div class="metric">
            <span class="metric-label">Function Name</span>
            <span class="metric-value">${FUNCTION_NAME}</span>
        </div>
        <div class="metric">
            <span class="metric-label">Invocations</span>
            <span class="metric-value">${INVOCATIONS:-0}</span>
        </div>
        <div class="metric">
            <span class="metric-label">Errors</span>
            <span class="metric-value">${ERRORS:-0}</span>
        </div>
        <div class="metric">
            <span class="metric-label">Average Duration</span>
            <span class="metric-value">${AVG_DURATION:-0} ms</span>
        </div>
    </div>

    <div class="section">
        <h2>Storage (S3)</h2>
        <div class="metric">
            <span class="metric-label">Bucket</span>
            <span class="metric-value">${S3_BUCKET}</span>
        </div>
        <div class="metric">
            <span class="metric-label">Object Count</span>
            <span class="metric-value">${OBJECT_COUNT:-0}</span>
        </div>
        <div class="metric">
            <span class="metric-label">Total Size</span>
            <span class="metric-value">${BUCKET_SIZE_GB:-0} GB</span>
        </div>
    </div>

    <div class="section">
        <h2>Database (DynamoDB)</h2>
        <div class="metric">
            <span class="metric-label">Table</span>
            <span class="metric-value">${DYNAMODB_TABLE}</span>
        </div>
        <div class="metric">
            <span class="metric-label">Total Items</span>
            <span class="metric-value">${ITEM_COUNT:-0}</span>
        </div>
        <div class="metric">
            <span class="metric-label">Total Manga</span>
            <span class="metric-value">${TOTAL_MANGA:-0}</span>
        </div>
        <div class="metric">
            <span class="metric-label">Total Chapters</span>
            <span class="metric-value">${TOTAL_CHAPTERS:-0}</span>
        </div>
        <div class="metric">
            <span class="metric-label">Total Images</span>
            <span class="metric-value">${TOTAL_IMAGES:-0}</span>
        </div>
    </div>

    <div class="footer">
        <p>Manga Scraper Monitoring System</p>
        <p>Report generated by generate-report.sh</p>
    </div>
</body>
</html>
EOF

success "HTML report saved: ${HTML_REPORT}"

echo ""
echo "========================================="
echo "Report Generation Complete!"
echo "========================================="
echo ""
echo "Reports saved:"
echo "  JSON: ${JSON_REPORT}"
echo "  HTML: ${HTML_REPORT}"
echo ""
echo "View HTML report:"
echo "  Open in browser: file://${HTML_REPORT}"
echo ""
