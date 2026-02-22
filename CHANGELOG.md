# Changelog

All notable changes to PropManager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### Tenant Management
- **Tenant Detail Modal** - Click-to-view tenant information from list
  - Overview tab with profile data and current lease
  - Leases tab with complete lease history
  - Billing tab with recent invoices and payments
  - Activity tab with work orders and onboarding sessions
  - Emergency contacts and vehicle information display
- **Tenant Archive/Restore** - Soft-delete tenants without data loss
  - Archive button deactivates tenant account
  - Restore button reactivates archived tenants
  - Archived tenants hidden from active lists
  - Separate archived tenant view with filter tabs
- **Tenant Deletion** - Permanent tenant removal with safeguards
  - Delete only tenants without active leases or billing
  - Confirmation modal shows all related data to be deleted
  - Cascading deletion of personal records (contacts, vehicles, insurance, etc.)
  - Delete blockers prevent accidental data loss

#### Onboarding Document Integration
- **Automatic Document Linking** - Onboarding uploads saved to tenant Documents
  - Insurance policy documents auto-saved to "Onboarding" folder
  - ID verification images (front/back) saved as Documents
  - Signed eDocuments auto-linked to lease and saved to Documents
  - Idempotent document creation prevents duplicates
  - All onboarding documents visible in tenant's Documents section

#### Lease-Document Linking
- **Admin Document Management** - Link documents and eDocuments to leases
  - Documents section on admin lease detail page
  - View all linked documents with download and unlink options
  - Separate display for signed eDocuments vs uploaded documents
  - Link existing documents modal with checkbox selection
  - Upload new documents directly from lease page
  - Automatic association of uploaded docs with lease/unit/tenant
- **Tenant Document Access** - View lease-related documents
  - Documents section on tenant lease detail page
  - Download signed eDocuments (lease agreements, etc.)
  - Download uploaded documents (insurance, ID, etc.)
  - Filtered to show only tenant-visible documents

### Fixed
- **Invoice Line Items** - Fixed InvoiceLineItem creation in onboarding
  - Changed `amount` parameter to `unit_price` to match model calculation
  - InvoiceLineItem now correctly calculates `amount = quantity * unit_price`
- **Template URL Namespace** - Fixed NoReverseMatch errors
  - Updated onboarding completion templates to use `accounts_tenant:tenant_dashboard`
  - Fixed tenant dashboard URL references throughout templates

#### Tenant Onboarding System
- **New Tenant Lease Flow** - Create leases for prospective tenants without accounts
  - Lease form with "New Tenant" mode (existing/new toggle)
  - Prospective tenant fields on Lease model (first_name, last_name, email, phone)
  - "Pending Onboarding" section in lease list with filter
  - Start onboarding directly from lease detail page
- **Complete Onboarding Wizard** - 15-step self-service tenant setup
  - Email verification with OTP
  - Account creation during onboarding
  - Personal information collection (DOB, SSN last 4, driver's license)
  - Emergency contacts, occupants, pets, vehicles
  - Employment and income verification
  - Renter's insurance upload
  - ID verification with document upload
  - eDocument signing integration
  - Move-in fee acknowledgment
  - Move-in date scheduling
- **Onboarding Templates** - Configurable templates per property
  - Enable/disable steps, set required steps
  - Custom welcome messages and property rules
  - Fee templates with lease field references
  - Document requirements from eDocument templates
- **Onboarding Presets** - 15 pre-built templates
  - Standard, Premium, Luxury rentals
  - Corporate, Furnished, Short-term
  - Student, Senior, Affordable housing
  - Military, Pet-friendly, International
  - Section 8, Co-living, ADA-accessible
- **Completion Automation**
  - Auto-link tenant to lease on completion
  - Transfer personal info to TenantProfile
  - Generate move-in invoices from template fees
  - Send completion notifications (tenant + admin)

#### Documentation
- Comprehensive documentation expansion
- Contributing guidelines (CONTRIBUTING.md)

---

## [1.0.0] - 2025-02-19

### Added

#### Core Platform
- Multi-property management with hierarchical organization
- Unit management with floor plans and amenity tracking
- Dual-portal architecture (Admin and Tenant portals)
- Role-based access control system
- Company settings and branding customization

#### Lease Management
- Complete lease lifecycle management
- Electronic signature workflow with token-based access
- Lease terms and addendum support
- Occupant and pet tracking
- Co-signer support
- Month-to-month and fixed-term lease types
- Automatic lease status transitions

#### Billing System
- Automated invoice generation with Django-Q2 tasks
- Property-level billing configuration
- Configurable late fees (flat or percentage-based)
- Grace period support
- Multiple billing items per invoice
- Partial payment tracking
- Invoice history and audit trail

#### Payment Processing
- **7 Payment Gateway Integrations:**
  - Stripe (credit/debit cards)
  - PayPal (wallet payments)
  - Square (in-person and online)
  - Authorize.Net (credit card processing)
  - Braintree (cards and PayPal)
  - Plaid ACH (bank transfers)
  - Bitcoin (cryptocurrency via BTCPay Server)
- Guided setup wizards for each gateway
- Webhook security with signature verification
- Payment method storage
- Automatic payment option

#### Tenant Rewards Program
- Streak-based reward tiers (3, 6, 12-month milestones)
- Prepayment bonuses (2, 3, 6-month incentives)
- Customizable reward amounts per property
- Reward tracking and history
- Automatic reward granting

#### Work Order System
- Tenant-initiated maintenance requests
- Photo and file attachments
- Priority and status tracking
- Contractor assignment with token access
- Work order notes and communication

#### Notifications System
- Multi-channel notifications (Email, SMS, In-App, Webhook)
- Notification groups for batch messaging
- Template-based notification content
- User notification preferences
- Notification history tracking

#### Communications
- Weather-based automated notifications
- Weather API integration (OpenWeatherMap)
- Automated weather alert workflows
- Email and SMS communication channels
- Twilio SMS integration

#### Document Management
- Lease document generation
- Signed document storage
- Document categorization
- Secure document access

#### Authentication
- OTP-based tenant authentication
- Magic link email login
- Session management
- Secure token generation

#### Background Tasks
- Django-Q2 integration for async processing
- Scheduled invoice generation
- Weather monitoring tasks
- Automatic late fee application
- Reward calculation tasks

#### Admin Features
- Comprehensive dashboard with KPIs
- Property and unit management
- Tenant management
- Financial reporting
- Work order management
- Communication tools
- System settings

#### Tenant Features
- Self-service tenant portal
- Payment history and online payments
- Work order submission
- Document access
- Lease viewing
- Notification preferences

### Technical
- Django 5.x framework
- PostgreSQL database
- Redis caching and task queue
- Bootstrap 5 responsive UI
- RESTful URL patterns
- Comprehensive seed data for testing

### Security
- CSRF protection
- Secure session handling
- Environment-based configuration
- Webhook signature verification
- Token expiration for signing links
- IP address logging for signatures

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2025-02-19 | Initial release |

---

## Upgrade Notes

### Upgrading to 1.0.0

This is the initial release. For fresh installations, follow the [deployment guide](docs/deployment.md).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for information on how to contribute to PropManager.
