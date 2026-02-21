# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

**DO NOT** create a public GitHub issue for security vulnerabilities.

Instead, please email security concerns to: **security@yourdomain.com**

Include the following information:

1. **Description** - Clear description of the vulnerability
2. **Steps to Reproduce** - Detailed steps to reproduce the issue
3. **Impact** - Potential impact of the vulnerability
4. **Affected Versions** - Which versions are affected
5. **Suggested Fix** - If you have one (optional)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt within 48 hours
- **Assessment**: We will assess the severity and impact
- **Updates**: We will keep you informed of our progress
- **Resolution**: We aim to resolve critical issues within 7 days
- **Credit**: We will credit reporters in our security advisories (unless anonymity is requested)

### Scope

The following are in scope for security reports:

- PropManager application code
- Authentication and authorization vulnerabilities
- Data exposure risks
- Injection vulnerabilities (SQL, XSS, etc.)
- Payment processing security issues
- API security issues

Out of scope:

- Social engineering attacks
- Physical security
- Denial of service attacks
- Issues in third-party dependencies (report to the respective project)

---

## Security Features

PropManager implements the following security measures:

### Authentication

- **OTP Authentication**: Tenants use passwordless magic link login
- **Session Management**: Secure session handling with configurable timeouts
- **Staff Authentication**: Standard Django authentication for admin users
- **Token-Based Access**: Secure, time-limited tokens for contractors and document signing

### Authorization

- **Role-Based Access Control**: Admin, Manager, Staff roles with different permissions
- **Property-Level Access**: Users can be restricted to specific properties
- **Tenant Isolation**: Tenants can only access their own data

### Data Protection

- **CSRF Protection**: Django's built-in CSRF protection on all forms
- **SQL Injection Prevention**: Django ORM prevents SQL injection
- **XSS Prevention**: Template auto-escaping prevents XSS
- **Secure Headers**: Recommended security headers for production

### Payment Security

- **PCI Compliance**: No card data stored locally - handled by payment gateways
- **Webhook Verification**: All payment webhooks verify signatures
- **Encrypted Communication**: HTTPS required for all payment operations

### E-Signature Security

- **Unique Tokens**: Cryptographically random signing tokens
- **Token Expiration**: Signing links expire after 7 days
- **IP Logging**: IP address recorded with each signature
- **Timestamp Recording**: Exact signing time recorded
- **Signature Storage**: Signatures stored as images with full audit trail

---

## Security Best Practices

### For Administrators

1. **Use Strong Passwords**: Admin accounts should use strong, unique passwords
2. **Enable 2FA**: Where possible, enable two-factor authentication
3. **Review Access**: Regularly audit user access and permissions
4. **Monitor Logs**: Review application logs for suspicious activity
5. **Keep Updated**: Apply security updates promptly

### For Deployment

1. **Use HTTPS**: Always serve over HTTPS in production
2. **Secure Environment Variables**: Never commit secrets to version control
3. **Database Security**: Use strong database passwords, restrict access
4. **Firewall Configuration**: Only expose necessary ports
5. **Regular Backups**: Maintain encrypted backups

### Environment Variables

Sensitive configuration should be in environment variables:

```bash
# Never commit these to version control
SECRET_KEY=<strong-random-key>
DATABASE_URL=<connection-string>
STRIPE_SECRET_KEY=<api-key>
TWILIO_AUTH_TOKEN=<token>
```

---

## Security Checklist

### Before Deployment

- [ ] `DEBUG = False` in production
- [ ] `SECRET_KEY` is unique and random
- [ ] `ALLOWED_HOSTS` is properly configured
- [ ] HTTPS is enforced
- [ ] Database credentials are secure
- [ ] All API keys are protected
- [ ] File permissions are restrictive
- [ ] Error pages don't expose sensitive information

### Recommended Settings

```python
# settings/production.py

DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com']

# Security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HTTPS
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Session security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True

# Content Security Policy (if using django-csp)
CSP_DEFAULT_SRC = ("'self'",)
```

---

## Incident Response

If you suspect a security incident:

1. **Contain**: Isolate affected systems if necessary
2. **Assess**: Determine the scope and impact
3. **Preserve**: Keep logs and evidence
4. **Notify**: Inform affected users if data was compromised
5. **Remediate**: Fix the vulnerability
6. **Review**: Conduct a post-incident review

---

## Security Updates

Security updates are released as patch versions (e.g., 1.0.1).

Subscribe to security notifications:
- Watch the GitHub repository
- Join the mailing list (if available)

---

## Compliance Considerations

### PCI DSS

PropManager is designed to minimize PCI scope:
- No card data is stored locally
- Payment processing is handled by certified gateways
- Webhook data does not include full card numbers

### GDPR

For EU users:
- User data can be exported
- Users can request data deletion
- Consent is obtained for data processing
- Data minimization principles are followed

### Data Retention

Configure data retention policies:
- Payment records: Keep for tax/legal requirements
- Logs: Rotate based on your retention policy
- Backups: Encrypt and secure

---

## Security Resources

- [Django Security Documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Payment Gateway Security](docs/services.md#webhook-security)

---

## Acknowledgments

We thank the following individuals for responsibly disclosing security issues:

*No reports yet - be the first!*

---

**Last Updated**: February 2025
