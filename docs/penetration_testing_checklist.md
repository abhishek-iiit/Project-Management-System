# Penetration Testing Checklist

This checklist covers security testing procedures for BugsTracker before production deployment and during regular security audits.

## Pre-Testing Preparation

### Scope Definition

- [ ] Define testing scope (URLs, IP ranges, functionalities)
- [ ] Define out-of-scope items (production data, third-party services)
- [ ] Obtain written authorization for testing
- [ ] Set up testing environment (staging/QA, not production)
- [ ] Backup all data before testing
- [ ] Notify team members about testing schedule

### Testing Environment

- [ ] Staging environment mirrors production
- [ ] Test data populated (realistic but not real PII)
- [ ] All features enabled and accessible
- [ ] Monitoring and logging enabled
- [ ] Restore process tested and documented

## OWASP Top 10 (2021) Testing

### 1. Broken Access Control

**Vertical Privilege Escalation:**
- [ ] Test if regular user can access admin endpoints
- [ ] Attempt to access `/admin/` without admin privileges
- [ ] Try to modify other users' data
- [ ] Test API endpoints with different user roles
- [ ] Verify object-level permissions (can user A edit user B's issues?)

**Horizontal Privilege Escalation:**
- [ ] Test if user from Org A can access Org B's data
- [ ] Attempt to view/edit projects from different organizations
- [ ] Test issue access across organizations
- [ ] Verify multi-tenancy isolation

**IDOR (Insecure Direct Object Reference):**
- [ ] Try accessing resources by guessing IDs
- [ ] Test sequential ID enumeration
- [ ] Verify UUID usage prevents enumeration
- [ ] Test with modified object IDs in API requests

**Missing Function Level Access Control:**
- [ ] Enumerate all API endpoints
- [ ] Test each endpoint without authentication
- [ ] Test each endpoint with different user roles
- [ ] Verify OPTIONS method responses don't leak information

### 2. Cryptographic Failures

**Data in Transit:**
- [ ] Verify HTTPS is enforced on all pages
- [ ] Test for HTTP to HTTPS redirect
- [ ] Check SSL/TLS certificate validity
- [ ] Test TLS version (should be 1.2+)
- [ ] Verify strong cipher suites only
- [ ] Test for SSL stripping attacks
- [ ] Check HSTS header presence and configuration

**Data at Rest:**
- [ ] Verify passwords are hashed (not encrypted or plaintext)
- [ ] Test password storage (Argon2 or similar)
- [ ] Check if sensitive data in database is encrypted
- [ ] Verify backup encryption
- [ ] Test API key storage encryption

**Sensitive Data Exposure:**
- [ ] Review API responses for sensitive data leakage
- [ ] Check browser developer tools for exposed tokens
- [ ] Verify no credentials in JavaScript
- [ ] Test for autocomplete on password fields
- [ ] Check error messages don't leak system info

### 3. Injection Attacks

**SQL Injection:**
- [ ] Test all input fields with SQL injection payloads
- [ ] Try: `' OR '1'='1`
- [ ] Try: `'; DROP TABLE users; --`
- [ ] Try: `' UNION SELECT null, username, password FROM users --`
- [ ] Test numeric parameters: `1 OR 1=1`
- [ ] Test search functionality
- [ ] Test sorting/filtering parameters
- [ ] Verify error messages don't expose SQL queries

**NoSQL Injection:**
- [ ] Test JSON inputs with NoSQL payloads
- [ ] Try: `{"$gt": ""}`
- [ ] Try: `{"$ne": null}`

**Command Injection:**
- [ ] Test file upload filenames
- [ ] Test URL parameters that interact with system
- [ ] Try: `; ls -la`
- [ ] Try: `| cat /etc/passwd`
- [ ] Try: `& whoami`

**LDAP Injection:**
- [ ] Test if LDAP is used for authentication
- [ ] Try: `*)(uid=*))(|(uid=*`

**XPath Injection:**
- [ ] Test XML processing inputs
- [ ] Try: `' or '1'='1`

### 4. Insecure Design

**Business Logic Flaws:**
- [ ] Test negative numbers in quantity fields
- [ ] Test price manipulation in orders
- [ ] Test race conditions (concurrent requests)
- [ ] Test workflow bypass (skip payment, skip approval)
- [ ] Test for logic flaws in multi-step processes
- [ ] Verify rate limiting on expensive operations

**Insufficient Resource Limits:**
- [ ] Test file upload size limits
- [ ] Test request body size limits
- [ ] Test pagination limits
- [ ] Test concurrent connection limits

### 5. Security Misconfiguration

**Default Credentials:**
- [ ] Test default admin credentials
- [ ] Test common username/password combinations
- [ ] Check for default API keys

**Directory Listing:**
- [ ] Try accessing `/static/`, `/media/`, `/uploads/`
- [ ] Verify directory listing is disabled

**Unnecessary Features:**
- [ ] Check for unnecessary HTTP methods (TRACE, PUT on GET resources)
- [ ] Verify debug mode is disabled
- [ ] Check for sample/demo data in production

**Verbose Error Messages:**
- [ ] Trigger 404, 500 errors
- [ ] Check for stack traces in responses
- [ ] Verify error messages don't expose system info

**Security Headers:**
- [ ] Check X-Content-Type-Options: nosniff
- [ ] Check X-Frame-Options: DENY
- [ ] Check X-XSS-Protection: 1; mode=block
- [ ] Check Strict-Transport-Security
- [ ] Check Content-Security-Policy
- [ ] Check Referrer-Policy

**Server Information Disclosure:**
- [ ] Check Server header (should not reveal version)
- [ ] Check X-Powered-By header (should be removed)
- [ ] Check for .git directory exposure

### 6. Vulnerable and Outdated Components

**Dependency Vulnerabilities:**
- [ ] Run `safety check` on Python dependencies
- [ ] Run `npm audit` on JavaScript dependencies
- [ ] Check Django version for known CVEs
- [ ] Check DRF version for known CVEs
- [ ] Verify all dependencies are up to date

**Third-Party Services:**
- [ ] Review third-party service security
- [ ] Check for known vulnerabilities in used libraries
- [ ] Verify CDN integrity with SRI hashes

### 7. Identification and Authentication Failures

**Brute Force Protection:**
- [ ] Test login rate limiting
- [ ] Attempt 100+ login attempts
- [ ] Test account lockout after failed attempts
- [ ] Test CAPTCHA after X failed attempts

**Weak Password Policy:**
- [ ] Try creating account with weak password
- [ ] Test: `password`, `123456`, `qwerty`
- [ ] Verify minimum length enforcement (12 chars)
- [ ] Verify complexity requirements

**Session Management:**
- [ ] Test session timeout
- [ ] Test logout functionality
- [ ] Verify session invalidation after logout
- [ ] Test concurrent session limits
- [ ] Check session ID entropy
- [ ] Test session fixation
- [ ] Test session hijacking

**Password Reset:**
- [ ] Test password reset token strength
- [ ] Test password reset token expiration
- [ ] Test password reset token reuse
- [ ] Verify email verification
- [ ] Test for user enumeration via reset

**JWT Token Security:**
- [ ] Test token expiration
- [ ] Test refresh token rotation
- [ ] Test token revocation
- [ ] Verify token signature validation
- [ ] Test algorithm confusion (change alg to none)
- [ ] Test token tampering

### 8. Software and Data Integrity Failures

**Insecure Deserialization:**
- [ ] Test pickle/yaml deserialization endpoints
- [ ] Test JSON deserialization with malicious payloads

**Integrity Verification:**
- [ ] Verify file upload integrity checks
- [ ] Check for digital signatures on updates
- [ ] Test auto-update mechanisms

**CI/CD Security:**
- [ ] Review pipeline security
- [ ] Check for secrets in build logs
- [ ] Verify artifact signing

### 9. Security Logging and Monitoring Failures

**Logging:**
- [ ] Verify login attempts are logged
- [ ] Verify failed access attempts are logged
- [ ] Verify sensitive operations are logged
- [ ] Check audit trail completeness
- [ ] Verify logs don't contain sensitive data (passwords, tokens)

**Monitoring:**
- [ ] Test alerting on suspicious activity
- [ ] Verify rate limit violations are logged
- [ ] Test incident response process

### 10. Server-Side Request Forgery (SSRF)

**SSRF Testing:**
- [ ] Test URL input fields with internal IPs
- [ ] Try: `http://localhost:8000/admin/`
- [ ] Try: `http://127.0.0.1/`
- [ ] Try: `http://169.254.169.254/` (cloud metadata)
- [ ] Try: `http://192.168.1.1/`
- [ ] Test webhook URLs
- [ ] Test image URL fetching
- [ ] Verify URL validation and whitelist

## Additional Security Tests

### Cross-Site Scripting (XSS)

**Reflected XSS:**
- [ ] Test search functionality
- [ ] Test error messages
- [ ] Test URL parameters reflected in page
- [ ] Payloads: `<script>alert(1)</script>`
- [ ] Payloads: `<img src=x onerror=alert(1)>`
- [ ] Payloads: `<svg onload=alert(1)>`

**Stored XSS:**
- [ ] Test comment fields
- [ ] Test issue descriptions
- [ ] Test profile bio/about
- [ ] Test file upload filenames
- [ ] Verify HTML sanitization

**DOM-based XSS:**
- [ ] Test JavaScript client-side rendering
- [ ] Test URL fragment processing
- [ ] Review JavaScript code for `innerHTML` usage

### Cross-Site Request Forgery (CSRF)

**CSRF Testing:**
- [ ] Verify CSRF token on all forms
- [ ] Test POST requests without CSRF token
- [ ] Test CSRF token validation
- [ ] Test SameSite cookie attribute
- [ ] Test double-submit cookie pattern

### Clickjacking

- [ ] Test for X-Frame-Options header
- [ ] Attempt to iframe the application
- [ ] Test CSP frame-ancestors directive

### File Upload Vulnerabilities

**File Upload Testing:**
- [ ] Upload executable files (.exe, .sh, .bat)
- [ ] Upload files with double extensions (.jpg.php)
- [ ] Upload files with null bytes (file.php%00.jpg)
- [ ] Upload extremely large files
- [ ] Upload files with malicious names
- [ ] Test MIME type validation
- [ ] Test file content validation
- [ ] Upload SVG with embedded JavaScript
- [ ] Test zip bomb (42.zip)
- [ ] Test path traversal in filenames

### API Security

**REST API Testing:**
- [ ] Test all HTTP methods (GET, POST, PUT, DELETE, PATCH)
- [ ] Test pagination bypass
- [ ] Test mass assignment
- [ ] Test for API key exposure
- [ ] Test rate limiting on all endpoints
- [ ] Test CORS configuration
- [ ] Verify Content-Type validation
- [ ] Test API versioning

**GraphQL (if used):**
- [ ] Test introspection queries
- [ ] Test query depth limits
- [ ] Test query complexity limits
- [ ] Test for information disclosure

### WebSocket Security

- [ ] Test WebSocket authentication
- [ ] Test message validation
- [ ] Test for XSS in WebSocket messages
- [ ] Test connection limits
- [ ] Test message rate limiting

### Email Security

- [ ] Test for email injection
- [ ] Test for open redirect in email links
- [ ] Verify SPF/DKIM/DMARC records
- [ ] Test unsubscribe functionality
- [ ] Test for sensitive data in emails

### Race Conditions

- [ ] Test concurrent requests to same endpoint
- [ ] Test double spending scenarios
- [ ] Test concurrent file uploads
- [ ] Test concurrent account creation

### Denial of Service

**Application DoS:**
- [ ] Test regex DoS (ReDoS)
- [ ] Test algorithmic complexity attacks
- [ ] Test resource exhaustion
- [ ] Test slowloris attack
- [ ] Test large file uploads
- [ ] Test zip bomb extraction

### Infrastructure Testing

**Network Security:**
- [ ] Port scan for open ports
- [ ] Test firewall rules
- [ ] Test SSH configuration
- [ ] Test for default services

**Container Security:**
- [ ] Test for container escape
- [ ] Review container privileges
- [ ] Test volume mounts
- [ ] Verify non-root user

**Kubernetes Security (if applicable):**
- [ ] Test RBAC configuration
- [ ] Test pod security policies
- [ ] Test network policies
- [ ] Test secrets management

## Mobile Application Testing (if applicable)

- [ ] Test insecure data storage
- [ ] Test SSL pinning
- [ ] Test token storage
- [ ] Test for hardcoded secrets
- [ ] Test deep link handling
- [ ] Test biometric authentication
- [ ] Reverse engineer APK/IPA
- [ ] Test root/jailbreak detection

## Post-Testing

### Reporting

- [ ] Document all vulnerabilities found
- [ ] Classify by severity (Critical, High, Medium, Low)
- [ ] Provide reproduction steps
- [ ] Include screenshots/evidence
- [ ] Suggest remediation steps
- [ ] Calculate CVSS scores

### Remediation

- [ ] Create tickets for all vulnerabilities
- [ ] Prioritize by severity
- [ ] Set remediation deadlines
- [ ] Retest after fixes
- [ ] Verify fix doesn't introduce new issues

### Validation

- [ ] Retest all fixed vulnerabilities
- [ ] Verify no regression
- [ ] Update security documentation
- [ ] Update this checklist based on findings

## Tools Used

### Automated Scanners
- [ ] OWASP ZAP
- [ ] Burp Suite
- [ ] Nikto
- [ ] SQLMap
- [ ] Nmap
- [ ] WPScan (if WordPress is used)

### Manual Testing Tools
- [ ] Burp Suite Pro
- [ ] Postman/Insomnia
- [ ] curl
- [ ] Browser Developer Tools

### Dependency Scanning
- [ ] Safety (Python)
- [ ] Bandit (Python)
- [ ] npm audit (JavaScript)
- [ ] Snyk
- [ ] Dependabot

## Compliance Checks

- [ ] GDPR compliance verification
- [ ] CCPA compliance verification
- [ ] PCI DSS (if handling payments)
- [ ] HIPAA (if handling health data)
- [ ] SOC 2 Type II requirements

## Sign-off

**Tested by:** ___________________
**Date:** ___________________
**Environment:** ___________________
**Findings:** ___________________
**Overall Security Rating:** ___________________

---

**Last Updated:** 2026-02-15
**Next Review:** Quarterly or before major releases
