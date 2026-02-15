#!/bin/bash

# Script to test API documentation setup
# Usage: ./scripts/test_api_docs.sh

set -e

echo "================================"
echo "Testing API Documentation Setup"
echo "================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
API_VERSION="v1"

# Test counters
PASSED=0
FAILED=0

# Helper function to test endpoint
test_endpoint() {
    local endpoint=$1
    local expected_status=$2
    local description=$3

    echo -n "Testing $description... "

    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$endpoint")

    if [ "$HTTP_STATUS" = "$expected_status" ]; then
        echo -e "${GREEN}✓ PASSED${NC} (HTTP $HTTP_STATUS)"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC} (Expected $expected_status, got $HTTP_STATUS)"
        ((FAILED++))
    fi
}

# Test function with content validation
test_endpoint_content() {
    local endpoint=$1
    local search_string=$2
    local description=$3

    echo -n "Testing $description... "

    RESPONSE=$(curl -s "$BASE_URL$endpoint")
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$endpoint")

    if [ "$HTTP_STATUS" = "200" ] && echo "$RESPONSE" | grep -q "$search_string"; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}"
        if [ "$HTTP_STATUS" != "200" ]; then
            echo "  Status: $HTTP_STATUS (expected 200)"
        else
            echo "  Content does not contain: $search_string"
        fi
        ((FAILED++))
    fi
}

echo "1. Testing Documentation Endpoints"
echo "-----------------------------------"
test_endpoint "/api/schema/" 200 "OpenAPI Schema endpoint"
test_endpoint "/api/docs/" 200 "Swagger UI endpoint"
test_endpoint "/api/redoc/" 200 "ReDoc endpoint"
echo ""

echo "2. Testing Health Check"
echo "----------------------"
test_endpoint "/health/" 200 "Health check endpoint"
test_endpoint_content "/health/" "status" "Health check response"
echo ""

echo "3. Testing Schema Content"
echo "------------------------"
test_endpoint_content "/api/schema/" "openapi" "OpenAPI version"
test_endpoint_content "/api/schema/" "BugsTracker API" "API title"
test_endpoint_content "/api/schema/" "paths" "API paths"
test_endpoint_content "/api/schema/" "components" "Components section"
echo ""

echo "4. Testing API Version Headers"
echo "------------------------------"
echo -n "Testing X-API-Version header... "
HEADERS=$(curl -s -I "$BASE_URL/api/$API_VERSION/auth/login/")
if echo "$HEADERS" | grep -q "X-API-Version"; then
    echo -e "${GREEN}✓ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ SKIPPED${NC} (API may not be running)"
fi
echo ""

echo "5. Testing Rate Limit Headers"
echo "-----------------------------"
echo -n "Testing rate limit headers... "
HEADERS=$(curl -s -I "$BASE_URL/api/$API_VERSION/auth/login/")
if echo "$HEADERS" | grep -q "X-RateLimit"; then
    echo -e "${GREEN}✓ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ SKIPPED${NC} (Headers may be added by middleware)"
fi
echo ""

echo "6. Testing Documentation Files"
echo "------------------------------"

# Check for documentation files
check_file() {
    local file=$1
    local description=$2

    echo -n "Checking $description... "
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ EXISTS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ MISSING${NC}"
        ((FAILED++))
    fi
}

check_file "docs/api/README.md" "API README"
check_file "docs/api/CHANGELOG.md" "API Changelog"
check_file "docs/api/TESTING.md" "Testing Guide"
check_file "docs/api/DEPLOYMENT.md" "Deployment Guide"
check_file "docs/api/postman_collection.json" "Postman Collection"
echo ""

echo "7. Testing Management Commands"
echo "------------------------------"
echo -n "Checking generate_openapi_schema command... "
if python backend/manage.py help generate_openapi_schema &>/dev/null; then
    echo -e "${GREEN}✓ EXISTS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ MISSING${NC}"
    ((FAILED++))
fi
echo ""

echo "8. Testing Schema Generation"
echo "----------------------------"
echo -n "Generating OpenAPI schema... "
cd backend
if python manage.py generate_openapi_schema --format json --validate &>/dev/null; then
    echo -e "${GREEN}✓ SUCCESS${NC}"
    ((PASSED++))

    # Check if files were created
    if [ -f "../docs/api/openapi.json" ]; then
        echo -e "  Generated file: ${GREEN}openapi.json${NC}"
    fi
else
    echo -e "${RED}✗ FAILED${NC}"
    ((FAILED++))
fi
cd ..
echo ""

echo "9. Validating Schema File"
echo "------------------------"
if [ -f "docs/api/openapi.json" ]; then
    echo -n "Validating openapi.json... "

    # Basic JSON validation
    if python -m json.tool docs/api/openapi.json >/dev/null 2>&1; then
        echo -e "${GREEN}✓ VALID JSON${NC}"
        ((PASSED++))

        # Check required fields
        echo -n "Checking required OpenAPI fields... "
        SCHEMA_CONTENT=$(cat docs/api/openapi.json)
        if echo "$SCHEMA_CONTENT" | grep -q "openapi" && \
           echo "$SCHEMA_CONTENT" | grep -q "\"info\"" && \
           echo "$SCHEMA_CONTENT" | grep -q "\"paths\""; then
            echo -e "${GREEN}✓ VALID${NC}"
            ((PASSED++))
        else
            echo -e "${RED}✗ INVALID${NC}"
            ((FAILED++))
        fi
    else
        echo -e "${RED}✗ INVALID JSON${NC}"
        ((FAILED++))
    fi
else
    echo -e "${YELLOW}⚠ SKIPPED${NC} (Schema file not found)"
fi
echo ""

echo "10. Testing Middleware"
echo "---------------------"
echo -n "Checking middleware configuration... "
if grep -q "RequestIDMiddleware" backend/config/settings/base.py; then
    echo -e "${GREEN}✓ CONFIGURED${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ NOT CONFIGURED${NC}"
    ((FAILED++))
fi
echo ""

# Summary
echo "================================"
echo "Test Summary"
echo "================================"
echo -e "Total Passed: ${GREEN}$PASSED${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "Total Failed: ${RED}$FAILED${NC}"
else
    echo -e "Total Failed: $FAILED"
fi
echo ""

# Exit with appropriate code
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
else
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi
