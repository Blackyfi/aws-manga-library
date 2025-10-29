#!/bin/bash
###############################################################################
# Update Dependencies Script
# ===========================
#
# Updates project dependencies for both Python and Node.js
# Checks for security vulnerabilities
# Creates backup before updating
#
# Usage: ./update-dependencies.sh [component] [mode]
# Components: python, nodejs, all
# Modes: check, update, security
# Example: ./update-dependencies.sh all update
###############################################################################

set -e  # Exit on error

# Configuration
COMPONENT="${1:-all}"
MODE="${2:-check}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "========================================="
echo "Update Dependencies"
echo "========================================="
echo "Component: ${COMPONENT}"
echo "Mode:      ${MODE}"
echo "Root:      ${PROJECT_ROOT}"
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

# Create backup directory
BACKUP_DIR="${PROJECT_ROOT}/.dependency-backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "${BACKUP_DIR}"

# Function to update Python dependencies
update_python_deps() {
    echo "========================================="
    echo "Python Dependencies"
    echo "========================================="
    echo ""

    SCRAPER_DIR="${PROJECT_ROOT}/scraper"

    if [ ! -d "${SCRAPER_DIR}" ]; then
        warning "Scraper directory not found, skipping Python updates"
        return
    fi

    cd "${SCRAPER_DIR}"

    # Check Python version
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is not installed"
        return
    fi

    PYTHON_VERSION=$(python3 --version)
    info "Python version: ${PYTHON_VERSION}"

    # Backup current requirements
    if [ -f "requirements.txt" ]; then
        cp requirements.txt "${BACKUP_DIR}/requirements.txt.bak"
        success "Backed up requirements.txt"
    fi

    if [ -f "requirements-dev.txt" ]; then
        cp requirements-dev.txt "${BACKUP_DIR}/requirements-dev.txt.bak"
        success "Backed up requirements-dev.txt"
    fi

    case "${MODE}" in
        check)
            info "Checking for outdated packages..."
            echo ""

            if [ -d "venv" ]; then
                source venv/bin/activate || source venv/Scripts/activate
            fi

            pip list --outdated || true

            echo ""
            info "To update packages, run: $0 python update"
            ;;

        update)
            info "Updating Python packages..."
            echo ""

            if [ -d "venv" ]; then
                source venv/bin/activate || source venv/Scripts/activate
            else
                warning "Virtual environment not found, creating one..."
                python3 -m venv venv
                source venv/bin/activate || source venv/Scripts/activate
            fi

            # Upgrade pip first
            pip install --upgrade pip

            # Update packages
            if [ -f "requirements.txt" ]; then
                info "Updating production dependencies..."
                pip install --upgrade -r requirements.txt
                pip freeze | grep -v "pkg-resources" > requirements.txt.new
                mv requirements.txt.new requirements.txt
                success "Production dependencies updated"
            fi

            if [ -f "requirements-dev.txt" ]; then
                info "Updating development dependencies..."
                pip install --upgrade -r requirements-dev.txt
                success "Development dependencies updated"
            fi

            echo ""
            success "Python dependencies updated successfully"
            ;;

        security)
            info "Checking for security vulnerabilities..."
            echo ""

            if [ -d "venv" ]; then
                source venv/bin/activate || source venv/Scripts/activate
            fi

            # Install safety if not present
            if ! command -v safety &> /dev/null; then
                pip install safety
            fi

            # Check with safety
            safety check --json > "${BACKUP_DIR}/python-security.json" || true

            VULN_COUNT=$(cat "${BACKUP_DIR}/python-security.json" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('vulnerabilities', [])))" 2>/dev/null || echo "0")

            if [ "${VULN_COUNT}" -gt 0 ]; then
                warning "Found ${VULN_COUNT} security vulnerabilities"
                cat "${BACKUP_DIR}/python-security.json"
            else
                success "No known security vulnerabilities found"
            fi

            # Also check with pip-audit if available
            if command -v pip-audit &> /dev/null; then
                info "Running pip-audit..."
                pip-audit || warning "pip-audit found issues"
            fi
            ;;
    esac

    echo ""
}

# Function to update Node.js dependencies
update_nodejs_deps() {
    echo "========================================="
    echo "Node.js Dependencies"
    echo "========================================="
    echo ""

    FRONTEND_DIR="${PROJECT_ROOT}/frontend"

    if [ ! -d "${FRONTEND_DIR}" ]; then
        warning "Frontend directory not found, skipping Node.js updates"
        return
    fi

    cd "${FRONTEND_DIR}"

    # Check Node.js version
    if ! command -v node &> /dev/null; then
        error "Node.js is not installed"
        return
    fi

    NODE_VERSION=$(node --version)
    NPM_VERSION=$(npm --version)
    info "Node.js version: ${NODE_VERSION}"
    info "npm version: ${NPM_VERSION}"

    # Backup package files
    if [ -f "package.json" ]; then
        cp package.json "${BACKUP_DIR}/package.json.bak"
        success "Backed up package.json"
    fi

    if [ -f "package-lock.json" ]; then
        cp package-lock.json "${BACKUP_DIR}/package-lock.json.bak"
        success "Backed up package-lock.json"
    fi

    case "${MODE}" in
        check)
            info "Checking for outdated packages..."
            echo ""

            npm outdated || true

            echo ""
            info "To update packages, run: $0 nodejs update"
            ;;

        update)
            info "Updating Node.js packages..."
            echo ""

            # Update npm first
            info "Updating npm..."
            npm install -g npm@latest || warning "Could not update npm globally"

            # Check for major updates
            if command -v npx &> /dev/null; then
                info "Checking for major updates with ncu..."
                npx npm-check-updates || warning "npm-check-updates not available"
            fi

            # Update dependencies
            info "Updating dependencies..."
            npm update

            # Audit fix
            info "Running npm audit fix..."
            npm audit fix || warning "Some issues could not be automatically fixed"

            echo ""
            success "Node.js dependencies updated successfully"
            ;;

        security)
            info "Checking for security vulnerabilities..."
            echo ""

            # Run npm audit
            npm audit --json > "${BACKUP_DIR}/npm-security.json" || true

            VULN_COUNT=$(cat "${BACKUP_DIR}/npm-security.json" | node -e "const fs = require('fs'); const data = JSON.parse(fs.readFileSync('/dev/stdin', 'utf8')); console.log(data.metadata?.vulnerabilities?.total || 0);" 2>/dev/null || echo "0")

            if [ "${VULN_COUNT}" -gt 0 ]; then
                warning "Found ${VULN_COUNT} security vulnerabilities"
                npm audit
                echo ""
                info "To fix automatically, run: npm audit fix"
                info "For breaking changes: npm audit fix --force"
            else
                success "No known security vulnerabilities found"
            fi
            ;;
    esac

    echo ""
}

# Function to run tests after update
run_tests() {
    echo "========================================="
    echo "Running Tests"
    echo "========================================="
    echo ""

    # Test Python
    if [ "${COMPONENT}" == "python" ] || [ "${COMPONENT}" == "all" ]; then
        info "Testing Python code..."
        cd "${PROJECT_ROOT}/scraper"

        if [ -d "venv" ]; then
            source venv/bin/activate || source venv/Scripts/activate
        fi

        if command -v pytest &> /dev/null; then
            pytest tests/ --tb=short || warning "Some Python tests failed"
        else
            warning "pytest not installed, skipping tests"
        fi

        echo ""
    fi

    # Test Node.js
    if [ "${COMPONENT}" == "nodejs" ] || [ "${COMPONENT}" == "all" ]; then
        info "Testing Node.js code..."
        cd "${PROJECT_ROOT}/frontend"

        if [ -f "package.json" ] && npm run | grep -q "test"; then
            npm test -- --passWithNoTests || warning "Some Node.js tests failed"
        else
            warning "No test script found, skipping tests"
        fi

        echo ""
    fi
}

# Main update logic
case "${COMPONENT}" in
    python)
        update_python_deps
        if [ "${MODE}" == "update" ]; then
            run_tests
        fi
        ;;

    nodejs)
        update_nodejs_deps
        if [ "${MODE}" == "update" ]; then
            run_tests
        fi
        ;;

    all)
        update_python_deps
        update_nodejs_deps
        if [ "${MODE}" == "update" ]; then
            run_tests
        fi
        ;;

    *)
        error "Unknown component: ${COMPONENT}"
        echo "Valid components: python, nodejs, all"
        exit 1
        ;;
esac

# Generate update report
REPORT_FILE="${PROJECT_ROOT}/.reports/dependencies-$(date +%Y%m%d-%H%M%S).txt"
mkdir -p "$(dirname ${REPORT_FILE})"

cat > "${REPORT_FILE}" <<EOF
Dependency Update Report
========================

Date: $(date)
Component: ${COMPONENT}
Mode: ${MODE}

Backups Location:
${BACKUP_DIR}

Python Dependencies:
$([ -f "${PROJECT_ROOT}/scraper/requirements.txt" ] && echo "$(wc -l < ${PROJECT_ROOT}/scraper/requirements.txt) packages" || echo "N/A")

Node.js Dependencies:
$([ -f "${PROJECT_ROOT}/frontend/package.json" ] && echo "$(cat ${PROJECT_ROOT}/frontend/package.json | grep -c '":' || echo '0') packages" || echo "N/A")

To restore from backup:
  cp ${BACKUP_DIR}/* [target directory]/

EOF

success "Report saved: ${REPORT_FILE}"

echo ""
echo "========================================="
echo "Update Complete!"
echo "========================================="
echo ""
echo "Backups saved to: ${BACKUP_DIR}"
echo "Report saved to: ${REPORT_FILE}"
echo ""

if [ "${MODE}" == "check" ]; then
    echo "Next steps:"
    echo "  1. Review outdated packages above"
    echo "  2. Run with 'update' mode: $0 ${COMPONENT} update"
    echo "  3. Test your application"
fi

if [ "${MODE}" == "security" ]; then
    echo "Next steps:"
    echo "  1. Review security issues above"
    echo "  2. Update vulnerable packages"
    echo "  3. Re-run security check"
fi

if [ "${MODE}" == "update" ]; then
    echo "Next steps:"
    echo "  1. Test your application thoroughly"
    echo "  2. Commit updated dependency files"
    echo "  3. Deploy updated application"
fi

echo ""
