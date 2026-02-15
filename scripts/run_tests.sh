#!/bin/bash

# Comprehensive test runner script for BugsTracker
# Usage: ./scripts/run_tests.sh [OPTIONS]

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_PATH="."
COVERAGE=true
PARALLEL=true
VERBOSE=false
MARKERS=""
REUSE_DB=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--path)
            TEST_PATH="$2"
            shift 2
            ;;
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        --no-parallel)
            PARALLEL=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -m|--markers)
            MARKERS="$2"
            shift 2
            ;;
        --no-reuse-db)
            REUSE_DB=false
            shift
            ;;
        -h|--help)
            echo "Usage: ./scripts/run_tests.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -p, --path PATH       Path to tests (default: .)"
            echo "  --no-coverage         Disable coverage reporting"
            echo "  --no-parallel         Disable parallel execution"
            echo "  -v, --verbose         Verbose output"
            echo "  -m, --markers MARKERS Run tests with specific markers"
            echo "  --no-reuse-db         Don't reuse database between runs"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./scripts/run_tests.sh                    # Run all tests"
            echo "  ./scripts/run_tests.sh -m unit            # Run unit tests only"
            echo "  ./scripts/run_tests.sh -p apps/issues     # Run issues app tests"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Change to backend directory
cd "$(dirname "$0")/../backend" || exit 1

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}🧪 Running BugsTracker Tests${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Activate virtual environment if it exists
if [ -d "../venv" ]; then
    source ../venv/bin/activate
fi

# Set test settings
export DJANGO_SETTINGS_MODULE=config.settings.test

# Build pytest command
PYTEST_CMD="pytest $TEST_PATH"

# Add verbose flag
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -vv"
fi

# Add markers
if [ -n "$MARKERS" ]; then
    PYTEST_CMD="$PYTEST_CMD -m $MARKERS"
fi

# Add database options
if [ "$REUSE_DB" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --reuse-db"
fi

# Add parallel execution
if [ "$PARALLEL" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -n auto --dist=loadfile"
fi

# Add coverage
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=apps --cov=config --cov-report=html --cov-report=term-missing --cov-report=xml --cov-fail-under=90"
fi

# Run tests
echo -e "${BLUE}Running: $PYTEST_CMD${NC}"
echo ""

eval "$PYTEST_CMD"

# Check exit code
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo -e "${GREEN}================================${NC}"

    if [ "$COVERAGE" = true ]; then
        echo ""
        echo -e "${BLUE}Coverage report:${NC} htmlcov/index.html"
    fi
else
    echo -e "${RED}================================${NC}"
    echo -e "${RED}❌ Some tests failed!${NC}"
    echo -e "${RED}================================${NC}"
    exit $EXIT_CODE
fi
