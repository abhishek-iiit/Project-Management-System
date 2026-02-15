#!/bin/bash

# Security Audit Script for BugsTracker
# Runs various security checks and generates a report

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Output file
REPORT_FILE="security_audit_$(date +%Y%m%d_%H%M%S).txt"

echo "============================================" | tee "$REPORT_FILE"
echo "BugsTracker Security Audit Report" | tee -a "$REPORT_FILE"
echo "Date: $(date)" | tee -a "$REPORT_FILE"
echo "============================================" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# Function to print section header
print_section() {
    echo -e "\n${BLUE}=== $1 ===${NC}" | tee -a "$REPORT_FILE"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓${NC} $1" | tee -a "$REPORT_FILE"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠${NC} $1" | tee -a "$REPORT_FILE"
}

# Function to print error
print_error() {
    echo -e "${RED}✗${NC} $1" | tee -a "$REPORT_FILE"
}

# Change to backend directory
cd "$(dirname "$0")/../../backend" || exit 1

# ============================================================================
# 1. Dependency Vulnerability Scan
# ============================================================================

print_section "1. Dependency Vulnerability Scan"

if command -v safety &> /dev/null; then
    echo "Running safety check..." | tee -a "$REPORT_FILE"
    if safety check --file requirements/production.txt 2>&1 | tee -a "$REPORT_FILE"; then
        print_success "No known vulnerabilities found in dependencies"
    else
        print_error "Vulnerabilities found in dependencies! Review above output."
    fi
else
    print_warning "safety not installed. Install with: pip install safety"
fi

# ============================================================================
# 2. Python Security Linting (Bandit)
# ============================================================================

print_section "2. Python Security Linting (Bandit)"

if command -v bandit &> /dev/null; then
    echo "Running bandit security scan..." | tee -a "$REPORT_FILE"
    if bandit -r apps/ config/ -f txt 2>&1 | tee -a "$REPORT_FILE"; then
        print_success "No security issues found by bandit"
    else
        print_warning "Potential security issues found. Review above output."
    fi
else
    print_warning "bandit not installed. Install with: pip install bandit"
fi

# ============================================================================
# 3. Secret Detection
# ============================================================================

print_section "3. Secret Detection"

echo "Checking for hardcoded secrets..." | tee -a "$REPORT_FILE"

# Check for common secret patterns
SECRET_PATTERNS=(
    "password\s*=\s*['\"][^'\"]+['\"]"
    "api_key\s*=\s*['\"][^'\"]+['\"]"
    "secret_key\s*=\s*['\"][^'\"]+['\"]"
    "AWS_ACCESS_KEY"
    "AWS_SECRET_ACCESS_KEY"
    "PRIVATE_KEY"
)

SECRETS_FOUND=0
for pattern in "${SECRET_PATTERNS[@]}"; do
    if grep -rn -E "$pattern" apps/ config/ 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" >> "$REPORT_FILE"; then
        SECRETS_FOUND=1
    fi
done

if [ $SECRETS_FOUND -eq 0 ]; then
    print_success "No hardcoded secrets detected"
else
    print_error "Potential hardcoded secrets found! Review report file."
fi

# ============================================================================
# 4. Django Security Check
# ============================================================================

print_section "4. Django Security Check"

echo "Running Django security check..." | tee -a "$REPORT_FILE"
if python manage.py check --deploy 2>&1 | tee -a "$REPORT_FILE"; then
    print_success "Django security check passed"
else
    print_warning "Django security check found issues. Review above output."
fi

# ============================================================================
# 5. File Permissions Check
# ============================================================================

print_section "5. File Permissions Check"

echo "Checking file permissions..." | tee -a "$REPORT_FILE"

# Check for overly permissive files
DANGEROUS_PERMS=0

# Check Python files
while IFS= read -r file; do
    perms=$(stat -f "%A" "$file" 2>/dev/null || stat -c "%a" "$file" 2>/dev/null)
    if [ "$perms" -gt 644 ]; then
        echo "Warning: $file has permissions $perms (should be 644 or less)" | tee -a "$REPORT_FILE"
        DANGEROUS_PERMS=1
    fi
done < <(find apps/ config/ -name "*.py" -type f)

if [ $DANGEROUS_PERMS -eq 0 ]; then
    print_success "File permissions are appropriate"
else
    print_warning "Some files have overly permissive permissions"
fi

# ============================================================================
# 6. HTTPS/SSL Configuration Check
# ============================================================================

print_section "6. HTTPS/SSL Configuration Check"

echo "Checking SSL/HTTPS settings..." | tee -a "$REPORT_FILE"

if grep -q "SECURE_SSL_REDIRECT = True" config/settings/production.py 2>/dev/null; then
    print_success "SSL redirect is enabled"
else
    print_error "SSL redirect is NOT enabled"
fi

if grep -q "SECURE_HSTS_SECONDS" config/settings/production.py 2>/dev/null; then
    print_success "HSTS is configured"
else
    print_warning "HSTS is not configured"
fi

if grep -q "SESSION_COOKIE_SECURE = True" config/settings/production.py 2>/dev/null; then
    print_success "Secure session cookies enabled"
else
    print_error "Secure session cookies NOT enabled"
fi

# ============================================================================
# 7. SQL Injection Prevention Check
# ============================================================================

print_section "7. SQL Injection Prevention Check"

echo "Checking for raw SQL queries..." | tee -a "$REPORT_FILE"

RAW_SQL_FOUND=0
if grep -rn "\.raw(" apps/ | grep -v ".pyc" | grep -v "__pycache__" >> "$REPORT_FILE"; then
    RAW_SQL_FOUND=1
fi

if grep -rn "\.execute(" apps/ | grep -v ".pyc" | grep -v "__pycache__" >> "$REPORT_FILE"; then
    RAW_SQL_FOUND=1
fi

if [ $RAW_SQL_FOUND -eq 0 ]; then
    print_success "No raw SQL queries found (using ORM)"
else
    print_warning "Raw SQL queries found. Ensure they use parameterization."
fi

# ============================================================================
# 8. XSS Prevention Check
# ============================================================================

print_section "8. XSS Prevention Check"

echo "Checking for potential XSS vulnerabilities..." | tee -a "$REPORT_FILE"

# Check for safe usage in templates
XSS_RISKS=0

# Check for |safe filter in templates
if find . -name "*.html" -type f -exec grep -l "|safe" {} \; 2>/dev/null >> "$REPORT_FILE"; then
    print_warning "Templates using |safe filter found. Ensure input is sanitized."
    XSS_RISKS=1
fi

# Check for mark_safe usage
if grep -rn "mark_safe" apps/ | grep -v ".pyc" >> "$REPORT_FILE"; then
    print_warning "mark_safe() usage found. Ensure input is sanitized."
    XSS_RISKS=1
fi

if [ $XSS_RISKS -eq 0 ]; then
    print_success "No obvious XSS risks found"
fi

# ============================================================================
# 9. CSRF Protection Check
# ============================================================================

print_section "9. CSRF Protection Check"

echo "Checking CSRF protection..." | tee -a "$REPORT_FILE"

if grep -q "django.middleware.csrf.CsrfViewMiddleware" config/settings/base.py 2>/dev/null; then
    print_success "CSRF middleware is enabled"
else
    print_error "CSRF middleware is NOT enabled"
fi

# Check for @csrf_exempt usage
if grep -rn "@csrf_exempt" apps/ | grep -v ".pyc" >> "$REPORT_FILE"; then
    print_warning "Views with @csrf_exempt found. Ensure this is intentional."
fi

# ============================================================================
# 10. Password Security Check
# ============================================================================

print_section "10. Password Security Check"

echo "Checking password security settings..." | tee -a "$REPORT_FILE"

if grep -q "Argon2PasswordHasher" config/settings/production.py 2>/dev/null; then
    print_success "Using Argon2 password hasher (most secure)"
else
    print_warning "Not using Argon2 password hasher"
fi

if grep -q "AUTH_PASSWORD_VALIDATORS" config/settings/base.py 2>/dev/null; then
    print_success "Password validators are configured"
else
    print_error "Password validators are NOT configured"
fi

# ============================================================================
# 11. Debug Mode Check
# ============================================================================

print_section "11. Debug Mode Check"

echo "Checking DEBUG setting..." | tee -a "$REPORT_FILE"

if grep -q "DEBUG = False" config/settings/production.py 2>/dev/null; then
    print_success "DEBUG is False in production"
else
    print_error "DEBUG is NOT False in production!"
fi

# ============================================================================
# 12. Secret Key Check
# ============================================================================

print_section "12. Secret Key Check"

echo "Checking SECRET_KEY configuration..." | tee -a "$REPORT_FILE"

if grep -q "os.environ.get('SECRET_KEY')" config/settings/production.py 2>/dev/null; then
    print_success "SECRET_KEY is loaded from environment"
else
    print_error "SECRET_KEY may be hardcoded!"
fi

# ============================================================================
# 13. Rate Limiting Check
# ============================================================================

print_section "13. Rate Limiting Check"

echo "Checking rate limiting configuration..." | tee -a "$REPORT_FILE"

if grep -q "RateLimitMiddleware" config/settings/production.py 2>/dev/null || \
   grep -q "DEFAULT_THROTTLE_CLASSES" config/settings/production.py 2>/dev/null; then
    print_success "Rate limiting is configured"
else
    print_warning "Rate limiting may not be configured"
fi

# ============================================================================
# 14. CORS Configuration Check
# ============================================================================

print_section "14. CORS Configuration Check"

echo "Checking CORS settings..." | tee -a "$REPORT_FILE"

if grep -q "CORS_ALLOWED_ORIGINS" config/settings/production.py 2>/dev/null; then
    print_success "CORS is configured"
else
    print_warning "CORS configuration not found"
fi

# Check for CORS_ALLOW_ALL_ORIGINS (dangerous)
if grep -q "CORS_ALLOW_ALL_ORIGINS = True" config/settings/ -r 2>/dev/null; then
    print_error "CORS_ALLOW_ALL_ORIGINS is True - this is dangerous!"
fi

# ============================================================================
# Summary
# ============================================================================

print_section "Audit Summary"

echo "" | tee -a "$REPORT_FILE"
echo "Audit completed. Full report saved to: $REPORT_FILE" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"
echo "Recommendations:" | tee -a "$REPORT_FILE"
echo "1. Review all warnings and errors in this report" | tee -a "$REPORT_FILE"
echo "2. Update dependencies with known vulnerabilities" | tee -a "$REPORT_FILE"
echo "3. Address any security issues found by bandit" | tee -a "$REPORT_FILE"
echo "4. Ensure no secrets are committed to version control" | tee -a "$REPORT_FILE"
echo "5. Review Django security checklist: https://docs.djangoproject.com/en/stable/howto/deployment/checklist/" | tee -a "$REPORT_FILE"
echo "6. Consider penetration testing for production deployment" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

print_success "Security audit complete!"
