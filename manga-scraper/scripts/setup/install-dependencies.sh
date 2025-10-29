#!/bin/bash
###############################################################################
# Dependency Installation Script
# ===============================
#
# Installs all required dependencies for the manga scraper project
# Supports both Python (scraper) and Node.js (frontend) dependencies
#
# Usage: ./install-dependencies.sh [component]
# Components: all, scraper, frontend
# Example: ./install-dependencies.sh all
###############################################################################

set -e  # Exit on error

# Configuration
COMPONENT="${1:-all}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "========================================="
echo "Dependency Installation"
echo "========================================="
echo "Component: ${COMPONENT}"
echo "Project Root: ${PROJECT_ROOT}"
echo ""

# Function to install Python dependencies
install_python_deps() {
    echo "Installing Python dependencies..."

    cd "${PROJECT_ROOT}/scraper"

    # Check Python version
    if ! command -v python3 &> /dev/null; then
        echo "Error: Python 3 is not installed"
        echo "Please install Python 3.11 or later"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    echo "  Python version: ${PYTHON_VERSION}"

    if (( $(echo "${PYTHON_VERSION} < 3.9" | bc -l) )); then
        echo "  Warning: Python 3.9+ recommended, you have ${PYTHON_VERSION}"
    fi

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "  Creating virtual environment..."
        python3 -m venv venv
        echo "  ✓ Virtual environment created"
    else
        echo "  ✓ Virtual environment already exists"
    fi

    # Activate virtual environment
    source venv/bin/activate || source venv/Scripts/activate

    # Upgrade pip
    echo "  Upgrading pip..."
    pip install --upgrade pip --quiet

    # Install production dependencies
    if [ -f "requirements.txt" ]; then
        echo "  Installing production dependencies..."
        pip install -r requirements.txt
        echo "  ✓ Production dependencies installed"
    fi

    # Install development dependencies
    if [ -f "requirements-dev.txt" ]; then
        echo "  Installing development dependencies..."
        pip install -r requirements-dev.txt
        echo "  ✓ Development dependencies installed"
    fi

    # Install package in editable mode
    if [ -f "setup.py" ]; then
        echo "  Installing package in editable mode..."
        pip install -e .
        echo "  ✓ Package installed"
    fi

    echo "✓ Python dependencies installed successfully"
    echo ""
}

# Function to install Node.js dependencies
install_nodejs_deps() {
    echo "Installing Node.js dependencies..."

    cd "${PROJECT_ROOT}/frontend"

    # Check Node.js version
    if ! command -v node &> /dev/null; then
        echo "Error: Node.js is not installed"
        echo "Please install Node.js 18 or later"
        echo "Visit: https://nodejs.org/"
        exit 1
    fi

    NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    echo "  Node.js version: v${NODE_VERSION}"

    if (( NODE_VERSION < 18 )); then
        echo "  Warning: Node.js 18+ recommended, you have v${NODE_VERSION}"
    fi

    # Check npm
    if ! command -v npm &> /dev/null; then
        echo "Error: npm is not installed"
        exit 1
    fi

    NPM_VERSION=$(npm --version)
    echo "  npm version: ${NPM_VERSION}"

    # Clean install
    if [ -d "node_modules" ]; then
        echo "  Cleaning existing node_modules..."
        rm -rf node_modules package-lock.json
    fi

    # Install dependencies
    echo "  Installing npm dependencies..."
    npm install

    echo "✓ Node.js dependencies installed successfully"
    echo ""
}

# Function to install system dependencies
install_system_deps() {
    echo "Checking system dependencies..."

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        echo "  ⚠ AWS CLI not installed"
        echo "    Install from: https://aws.amazon.com/cli/"
    else
        AWS_VERSION=$(aws --version 2>&1 | cut -d' ' -f1 | cut -d'/' -f2)
        echo "  ✓ AWS CLI: ${AWS_VERSION}"
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo "  ⚠ Docker not installed (optional)"
        echo "    Install from: https://www.docker.com/"
    else
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
        echo "  ✓ Docker: ${DOCKER_VERSION}"
    fi

    # Check Git
    if ! command -v git &> /dev/null; then
        echo "  ⚠ Git not installed"
    else
        GIT_VERSION=$(git --version | cut -d' ' -f3)
        echo "  ✓ Git: ${GIT_VERSION}"
    fi

    echo ""
}

# Main installation flow
case "${COMPONENT}" in
    scraper)
        install_system_deps
        install_python_deps
        ;;
    frontend)
        install_system_deps
        install_nodejs_deps
        ;;
    all)
        install_system_deps
        install_python_deps
        install_nodejs_deps
        ;;
    *)
        echo "Error: Unknown component '${COMPONENT}'"
        echo "Valid options: all, scraper, frontend"
        exit 1
        ;;
esac

echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""

case "${COMPONENT}" in
    scraper|all)
        echo "Python (Scraper):"
        echo "  Activate venv: source ${PROJECT_ROOT}/scraper/venv/bin/activate"
        echo "  Run tests: cd ${PROJECT_ROOT}/scraper && pytest"
        echo "  Run example: cd ${PROJECT_ROOT}/scraper && python scripts/example_usage.py"
        echo ""
        ;;
esac

case "${COMPONENT}" in
    frontend|all)
        echo "Node.js (Frontend):"
        echo "  Start dev server: cd ${PROJECT_ROOT}/frontend && npm run dev"
        echo "  Run tests: cd ${PROJECT_ROOT}/frontend && npm test"
        echo "  Build: cd ${PROJECT_ROOT}/frontend && npm run build"
        echo ""
        ;;
esac

echo "Next steps:"
echo "  1. Configure AWS credentials: aws configure"
echo "  2. Create .env files for each component"
echo "  3. Set up AWS resources: ./scripts/setup/create-aws-resources.sh"
echo ""
