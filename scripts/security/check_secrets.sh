#!/bin/bash

# Check for hardcoded secrets in the codebase
# This script should be run as part of CI/CD pipeline

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================"
echo "Checking for hardcoded secrets..."
echo "============================================"
echo ""

SECRETS_FOUND=0

# Change to repository root
cd "$(dirname "$0")/../.." || exit 1

# Patterns to search for
declare -a PATTERNS=(
    "password\s*=\s*['\"][^'\"]{3,}['\"]"
    "api_key\s*=\s*['\"][^'\"]{10,}['\"]"
    "secret_key\s*=\s*['\"][^'\"]{20,}['\"]"
    "AWS_ACCESS_KEY_ID\s*=\s*['\"][A-Z0-9]{20}['\"]"
    "AWS_SECRET_ACCESS_KEY\s*=\s*['\"][A-Za-z0-9/+=]{40}['\"]"
    "PRIVATE_KEY"
    "BEGIN RSA PRIVATE KEY"
    "BEGIN DSA PRIVATE KEY"
    "BEGIN EC PRIVATE KEY"
    "BEGIN OPENSSH PRIVATE KEY"
    "github_token"
    "oauth_token"
    "authorization:\s*Bearer"
)

# Files/directories to exclude
EXCLUDE_PATTERNS=(
    ".git"
    "node_modules"
    "__pycache__"
    "*.pyc"
    ".env.example"
    "*.md"
    "check_secrets.sh"
)

# Build exclude parameters for grep
EXCLUDE_PARAMS=""
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    EXCLUDE_PARAMS+=" --exclude=$pattern"
done

echo "Scanning for sensitive patterns..."
echo ""

# Search for each pattern
for pattern in "${PATTERNS[@]}"; do
    echo -e "${YELLOW}Searching for: $pattern${NC}"

    if grep -rniE $EXCLUDE_PARAMS "$pattern" . 2>/dev/null; then
        echo -e "${RED}✗ Found potential secret!${NC}"
        SECRETS_FOUND=1
    else
        echo -e "${GREEN}✓ No matches${NC}"
    fi
    echo ""
done

# Check for high entropy strings (potential secrets)
echo -e "${YELLOW}Checking for high entropy strings...${NC}"

# Look for long alphanumeric strings that might be secrets
if grep -rniE $EXCLUDE_PARAMS "['\"][A-Za-z0-9]{32,}['\"]" . 2>/dev/null | grep -v "test" | grep -v "example" | head -20; then
    echo -e "${YELLOW}⚠ Found high entropy strings (may be false positives)${NC}"
    echo "Review above results manually"
else
    echo -e "${GREEN}✓ No suspicious high entropy strings${NC}"
fi
echo ""

# Check for common secret file names
echo -e "${YELLOW}Checking for secret files...${NC}"

SECRET_FILES=(
    ".env"
    "credentials.json"
    "secret.key"
    "private.key"
    "id_rsa"
    "id_dsa"
    ".npmrc"
    ".pypirc"
)

for file in "${SECRET_FILES[@]}"; do
    if find . -name "$file" -not -path "./.git/*" -not -path "./node_modules/*" | grep -q .; then
        echo -e "${RED}✗ Found secret file: $file${NC}"
        find . -name "$file" -not -path "./.git/*" -not -path "./node_modules/*"
        SECRETS_FOUND=1
    fi
done

if [ $SECRETS_FOUND -eq 0 ]; then
    echo -e "${GREEN}✓ No secret files found${NC}"
fi
echo ""

# Check git history for secrets (if detect-secrets is installed)
if command -v detect-secrets &> /dev/null; then
    echo -e "${YELLOW}Running detect-secrets scan...${NC}"

    if detect-secrets scan --all-files --force-use-all-plugins 2>&1; then
        echo -e "${GREEN}✓ detect-secrets scan passed${NC}"
    else
        echo -e "${RED}✗ detect-secrets found potential secrets${NC}"
        SECRETS_FOUND=1
    fi
else
    echo -e "${YELLOW}⚠ detect-secrets not installed. Install with: pip install detect-secrets${NC}"
fi
echo ""

# Summary
echo "============================================"
echo "Secret Scanning Summary"
echo "============================================"

if [ $SECRETS_FOUND -eq 0 ]; then
    echo -e "${GREEN}✓ No secrets detected!${NC}"
    echo ""
    echo "Remember:"
    echo "- Always use environment variables for secrets"
    echo "- Never commit .env files"
    echo "- Use .gitignore to exclude secret files"
    echo "- Rotate secrets if accidentally committed"
    exit 0
else
    echo -e "${RED}✗ Potential secrets detected!${NC}"
    echo ""
    echo "Action items:"
    echo "1. Review all findings above"
    echo "2. Remove hardcoded secrets"
    echo "3. Use environment variables instead"
    echo "4. If secrets were committed, rotate them immediately"
    echo "5. Consider using git-secrets or detect-secrets pre-commit hook"
    exit 1
fi
