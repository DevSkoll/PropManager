# PropManager Documentation

Welcome to the PropManager documentation! This guide covers everything you need to know about using, configuring, and developing PropManager.

---

## Quick Links

| I want to... | Go to... |
|--------------|----------|
| Set up PropManager locally | [Getting Started](development/getting-started.md) |
| Deploy to production | [Deployment Guide](deployment.md) |
| Learn the admin portal | [Admin Guide](guides/admin-guide.md) |
| Use the tenant portal | [Tenant Guide](guides/tenant-guide.md) |
| Fix an issue | [Troubleshooting](troubleshooting.md) |
| Contribute code | [Contributing](../CONTRIBUTING.md) |

---

## Documentation Overview

### User Guides

Guides for using PropManager portals.

| Guide | Description |
|-------|-------------|
| [Admin Guide](guides/admin-guide.md) | Complete guide to the admin portal - properties, tenants, leases, billing, and more |
| [Tenant Guide](guides/tenant-guide.md) | How tenants use the portal - payments, work orders, documents |
| [Onboarding Guide](guides/onboarding-guide.md) | New tenant onboarding workflow - from lease creation to move-in |
| [Contractor Guide](guides/contractor-guide.md) | Token-based access for contractors to view and update work orders |

### Technical Documentation

Architecture and configuration details.

| Document | Description |
|----------|-------------|
| [Architecture](architecture.md) | System design, data models, authentication flows |
| [Services](services.md) | Payment gateways, SMS, email, weather API integrations |
| [Deployment](deployment.md) | Production setup with Nginx, SSL, and systemd |

### Developer Resources

For those contributing to or customizing PropManager.

| Document | Description |
|----------|-------------|
| [Getting Started](development/getting-started.md) | Local development environment setup |
| [Workflow](development/workflow.md) | Git branching, commits, pull requests |
| [Background Tasks](development/tasks.md) | Django-Q2 task architecture and creation |

### Reference

Detailed technical reference material.

| Document | Description |
|----------|-------------|
| [API Reference](reference/api.md) | URL endpoints and view documentation |
| [Management Commands](reference/commands.md) | Custom Django management commands |
| [Troubleshooting](troubleshooting.md) | Common issues and solutions |

---

## Feature Overview

### Core Features

- **Multi-Property Management** - Manage multiple properties and units from one dashboard
- **Tenant Portal** - Self-service portal for tenants with OTP authentication
- **Lease Management** - Full lease lifecycle with electronic signatures
- **Billing System** - Automated invoicing with configurable late fees
- **Payment Processing** - 7 payment gateway integrations
- **Tenant Onboarding** - Automated wizard for new tenant setup with 15 configurable presets
- **eDocuments** - Template-based electronic document signing with variable substitution
- **Global Search** - Unified search across apps, tenants, properties, documents, and more

### Payment Gateways

| Gateway | Payment Types |
|---------|--------------|
| Stripe | Credit/debit cards |
| PayPal | PayPal wallet |
| Square | Cards, in-person |
| Authorize.Net | Credit card processing |
| Braintree | Cards, PayPal |
| Plaid ACH | Bank transfers |
| Bitcoin | Cryptocurrency |

### Additional Features

- **Work Orders** - Maintenance request system with contractor access
- **Rewards Program** - Streak and prepayment incentives
- **Weather Notifications** - Automated severe weather alerts
- **Document Management** - Lease storage and signed documents
- **Multi-Channel Notifications** - Email, SMS, in-app, webhooks
- **AWS-Style Navigation** - App launcher with search, pinned apps, and recent history
- **Onboarding Presets** - 15 pre-configured templates (standard, corporate, military, student, etc.)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      PropManager                             │
├─────────────────┬───────────────────┬───────────────────────┤
│  Admin Portal   │   Tenant Portal   │   Contractor Access   │
│  (Staff/Mgmt)   │   (Residents)     │   (Token-based)       │
├─────────────────┴───────────────────┴───────────────────────┤
│                     Django Application                       │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│ Accounts │ Leases   │ Billing  │  Work    │   Documents     │
│Properties│ Lifecycle│ Rewards  │  Orders  │ Communications  │
├──────────┴──────────┴──────────┴──────────┴─────────────────┤
│                     Django-Q2 Task Queue                     │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL       │     Redis        │   File Storage       │
│  (Database)       │   (Cache/Queue)  │   (Documents)        │
└───────────────────┴──────────────────┴──────────────────────┘
```

For detailed architecture information, see [Architecture](architecture.md).

---

## Getting Help

### For Users

- Check the [Troubleshooting Guide](troubleshooting.md) for common issues
- Contact your system administrator

### For Developers

- Review existing [GitHub Issues](https://github.com/yourusername/propmanager/issues)
- Read the [Contributing Guidelines](../CONTRIBUTING.md)
- Check the [Development Docs](development/getting-started.md)

### Security Issues

For security vulnerabilities, see [SECURITY.md](../SECURITY.md) for responsible disclosure.

---

## Version Information

- **Current Version**: 1.0.0
- **Django**: 5.x
- **Python**: 3.11+
- **Database**: PostgreSQL 14+

See [CHANGELOG.md](../CHANGELOG.md) for version history.

---

## License

PropManager is licensed under **AGPL-3.0**. See [LICENSE](../LICENSE) for details.

For dual-licensing inquiries, contact the maintainers.
