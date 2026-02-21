# Admin Portal Guide

This comprehensive guide covers all features available in the PropManager Admin Portal.

## Table of Contents

- [Getting Started](#getting-started)
- [Navigation & Search](#navigation--search)
- [Dashboard Overview](#dashboard-overview)
- [Property Management](#property-management)
- [Unit Management](#unit-management)
- [Tenant Management](#tenant-management)
- [Tenant Onboarding](#tenant-onboarding)
- [Lease Management](#lease-management)
- [eDocuments](#edocuments)
- [Billing Configuration](#billing-configuration)
- [Invoice Management](#invoice-management)
- [Payment Processing](#payment-processing)
- [Work Orders](#work-orders)
- [Rewards Program](#rewards-program)
- [Communications](#communications)
- [Weather Notifications](#weather-notifications)
- [Reports](#reports)
- [Settings](#settings)

---

## Getting Started

### Accessing the Admin Portal

1. Navigate to `/admin-portal/` on your PropManager instance
2. Log in with your admin credentials
3. You'll be directed to the dashboard

### Navigation

The admin portal uses an AWS-style launcher navigation with:

- **Top Navigation Bar** - Always visible with search and quick access
- **App Launcher** - Grid of all apps organized by category
- **Global Search** - Search across apps, tenants, properties, and more
- **Recent Apps** - Quick access to recently used features

See [Navigation & Search](#navigation--search) for detailed usage.

---

## Navigation & Search

### App Launcher

Click the grid icon (☰) in the top navigation to open the app launcher:

1. **Pinned Apps** - Your favorite apps (click pin icon to add)
2. **Recent Apps** - Last 6 apps you've used
3. **Categories** - All apps organized by function:
   - Dashboard & Analytics
   - Properties & Units
   - Tenants & Leases
   - Billing & Payments
   - Maintenance & Work Orders
   - Communications & Notifications
   - Documents & Templates
   - Settings & Configuration

### Global Search

The search bar in the top navigation searches across all entities:

**How to Use:**
1. Click the search bar or press `Ctrl/Cmd + K`
2. Type at least 2 characters
3. Results appear instantly, grouped by category

**Search Categories (in priority order):**

| Category | What's Searched |
|----------|-----------------|
| Apps | App names, descriptions, keywords |
| Tenants | Name, email, phone |
| Properties | Name, address, city |
| Units | Unit number, property name |
| Leases | Tenant name, unit number |
| Documents | Title, template name |
| Work Orders | Title, description |
| Invoices | Invoice number, tenant name |

**Keyboard Navigation:**
- `↓` / `↑` - Move between results
- `Enter` - Open selected result
- `Escape` - Close search

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + K` | Focus search bar |
| `Ctrl/Cmd + /` | Open app launcher |
| `Escape` | Close modal/search |

### Customization

**Pin Apps:**
1. Open the app launcher
2. Hover over any app tile
3. Click the pin icon in the corner
4. Pinned apps appear at the top of the launcher

**Recent Apps:**
- Automatically tracked as you navigate
- Shows last 8 apps used
- Available in launcher and dropdown menu

---

## Dashboard Overview

The dashboard provides a quick overview of your portfolio:

### Key Metrics

- **Total Properties** - Number of managed properties
- **Total Units** - Total unit count across all properties
- **Occupancy Rate** - Percentage of occupied units
- **Monthly Revenue** - Current month's collected rent
- **Outstanding Balance** - Total unpaid invoices
- **Open Work Orders** - Pending maintenance requests

### Recent Activity

- Latest lease signings
- Recent payments received
- New work order submissions
- Upcoming lease expirations

### Quick Actions

- Add new property
- Create tenant account
- Generate invoices
- View overdue payments

---

## Property Management

### Adding a Property

1. Navigate to **Properties** → **Add Property**
2. Fill in property details:
   - **Name** - Property name/identifier
   - **Address** - Full street address
   - **City, State, ZIP** - Location details
   - **Property Type** - Residential, commercial, mixed-use
   - **Year Built** - Construction year
   - **Total Units** - Number of units
3. Upload property photos (optional)
4. Click **Save Property**

### Property Settings

Each property has configurable settings:

- **General** - Name, address, contact info
- **Billing** - Late fees, grace periods (see [Billing Configuration](#billing-configuration))
- **Rewards** - Tenant reward program settings
- **Documents** - Property-level document templates

### Property Features

- **Amenities** - Pool, gym, laundry, parking, etc.
- **Pet Policy** - Allowed pets, restrictions, deposits
- **Smoking Policy** - Property-wide or unit-specific
- **Parking** - Available spaces, assigned parking

---

## Unit Management

### Adding Units

1. Navigate to a property's detail page
2. Click **Add Unit**
3. Enter unit details:
   - **Unit Number** - Identifier (e.g., "101", "A", "Suite 200")
   - **Floor** - Floor level
   - **Bedrooms** - Number of bedrooms
   - **Bathrooms** - Number of bathrooms
   - **Square Footage** - Unit size
   - **Base Rent** - Default monthly rent
4. Click **Save Unit**

### Unit Status

Units can have the following statuses:

| Status | Description |
|--------|-------------|
| Available | Ready to lease |
| Occupied | Currently leased |
| Maintenance | Under repair/renovation |
| Reserved | Held for upcoming lease |

### Unit Amenities

Track unit-specific features:

- Appliances (dishwasher, washer/dryer, etc.)
- Flooring type
- HVAC system
- Storage space
- Balcony/patio
- View type

---

## Tenant Management

### Creating Tenant Accounts

1. Navigate to **Tenants** → **Add Tenant**
2. Enter tenant information:
   - **Email** - Primary contact (used for login)
   - **First Name / Last Name**
   - **Phone Number**
   - **Emergency Contact** (optional)
3. Click **Create Tenant**

The tenant will receive an email with login instructions.

### Tenant Authentication

PropManager uses OTP (One-Time Password) authentication:

1. Tenant enters email address
2. System sends a magic link via email
3. Tenant clicks link to log in
4. Session is established

No passwords to remember or reset.

### Tenant Profile

View and manage tenant information:

- Contact details
- Lease history
- Payment history
- Work order history
- Documents
- Reward points balance

---

## Tenant Onboarding

The tenant onboarding system automates the process of bringing new tenants into PropManager.

### How It Works

1. **Admin creates onboarding session** for a prospective tenant
2. **System sends invitation** via email/SMS with unique link
3. **Tenant completes wizard** - account creation, info collection, document signing, payments
4. **System creates tenant account** and links to lease

### Creating an Onboarding Session

1. Navigate to **Tenants** → **Onboarding** → **New Session**
2. Select the property and unit
3. Enter prospective tenant information:
   - Email address
   - Phone number (optional)
   - First and last name
4. Choose an onboarding template
5. Click **Send Invitation**

The tenant receives an email with a secure link to begin onboarding.

### Onboarding Templates

Templates define which steps are required during onboarding:

| Step | Description | Configurable |
|------|-------------|--------------|
| Account Creation | OTP verification and account setup | Required |
| Personal Info | Name, DOB, contact preferences | Required |
| Emergency Contacts | Primary and secondary contacts | Required |
| Occupants | Additional household members | Optional |
| Pets | Pet registration | Optional |
| Vehicles | Vehicle registration for parking | Optional |
| Employment | Income/employer verification | Optional |
| Renter's Insurance | Policy upload or waiver | Optional |
| Documents | eSigning leases and agreements | Required |
| Payments | Move-in costs (deposit, first month, fees) | Required |
| Welcome | Property info and move-in checklist | Required |

### Managing Templates

1. Navigate to **Settings** → **Onboarding Templates**
2. View existing templates or create new
3. Configure:
   - Which steps are enabled
   - Which steps are required
   - Step order
   - Welcome message and property rules
   - Required documents (from eDocument templates)
   - Required fees (security deposit, first month, etc.)

### Onboarding Presets

PropManager includes 15 pre-configured presets for common scenarios:

**Standard:**
- Standard Residential
- Pet-Friendly Property
- Luxury/High-End

**Specialized:**
- Senior Living (55+)
- Student Housing
- Low-Income/Section 8
- Corporate Relocation
- Military Housing (PCS/BAH)
- Lease Renewal (Existing Tenant)

### Session Management

Monitor onboarding progress:

1. Navigate to **Tenants** → **Onboarding** → **Sessions**
2. View all sessions with status:
   - **Invited** - Link sent, not yet clicked
   - **Started** - Tenant has begun the process
   - **Completed** - All steps finished
   - **Expired** - Link expired (can regenerate)
   - **Cancelled** - Admin cancelled session

### Session Actions

- **View Details** - See progress and collected information
- **Resend Invitation** - Send reminder email/SMS
- **Regenerate Link** - Create new token (extends expiration)
- **Cancel** - Cancel the onboarding process

---

## Lease Management

### Creating a Lease

1. Navigate to **Leases** → **Create Lease**
2. Select tenant and unit
3. Configure lease terms:
   - **Lease Type** - Fixed-term or month-to-month
   - **Start Date** - Lease commencement
   - **End Date** - Lease expiration (fixed-term only)
   - **Monthly Rent** - Base rent amount
   - **Security Deposit** - Required deposit
   - **Rent Due Day** - Day of month rent is due (1-28)

### Lease Policies

Configure policies for each lease:

- **Pets** - Allowed/not allowed, maximum number, pet deposit
- **Smoking** - Allowed/not allowed
- **Subletting** - Allowed/not allowed
- **Maximum Occupants** - Occupancy limit
- **Parking Spaces** - Assigned parking count
- **Renters Insurance** - Required/optional, minimum coverage

### Lease Terms

Add custom terms and conditions:

1. Go to lease detail page
2. Click **Add Term**
3. Enter:
   - **Title** - Term heading
   - **Description** - Full term text
   - **Is Standard** - Mark as standard term for reuse

### Occupants

Add additional occupants to the lease:

1. Go to lease detail page → **Occupants** section
2. Click **Add Occupant**
3. Enter:
   - **Name** - Full name
   - **Relationship** - Spouse, child, roommate, etc.
   - **Is on Lease** - Whether they sign the lease
   - **Is Cosigner** - Whether they are a co-signer
   - **Email** - For signing notifications

### Pets

Register pets on the lease:

1. Go to lease detail page → **Pets** section
2. Click **Add Pet**
3. Enter:
   - **Name** - Pet name
   - **Type** - Dog, cat, bird, etc.
   - **Breed** - Specific breed
   - **Weight** - Pet weight
   - **Is Service Animal** - ESA or service animal designation

### Fees

Add recurring or one-time fees:

1. Go to lease detail page → **Fees** section
2. Click **Add Fee**
3. Enter:
   - **Name** - Fee description
   - **Amount** - Fee amount
   - **Frequency** - One-time, monthly, annually

### E-Signatures

PropManager includes built-in electronic signature functionality:

#### Sending for Signatures

1. Go to lease detail page
2. Click **Send for Signatures**
3. Review the list of required signers:
   - Primary tenant
   - Occupants marked "on lease"
   - Co-signers
4. Click **Send for Signatures**

#### Signature Process

1. Each signer receives an email with a unique signing link
2. Links expire after 7 days for security
3. Signer views the lease terms
4. Signer draws their signature on the canvas
5. Signer types their full name for confirmation
6. Signature is recorded with timestamp and IP address

#### Signature Status

| Status | Description |
|--------|-------------|
| Draft | Not yet sent for signatures |
| Pending | Sent, waiting for all signatures |
| Partial | Some signatures collected |
| Executed | All signatures collected |

---

## eDocuments

PropManager includes a full electronic document system for creating, sending, and signing documents.

### Document Templates

Create reusable templates with dynamic content:

1. Navigate to **Documents** → **eDoc Templates**
2. Click **Create Template**
3. Enter:
   - **Name** - Template identifier
   - **Type** - Lease, Pet Agreement, Addendum, Notice, etc.
   - **Content** - Markdown with variables and signature tags

### Template Variables

Use variables that auto-populate with lease/tenant data:

```markdown
This lease agreement is between **{{property_name}}** ("Landlord")
and **{{tenant_name}}** ("Tenant") for the unit located at:

**{{property_address}}, Unit {{unit_number}}**

**Lease Term:** {{lease_start_date}} to {{lease_end_date}}
**Monthly Rent:** ${{monthly_rent}}
**Security Deposit:** ${{security_deposit}}
```

**Available Variables:**

| Variable | Description |
|----------|-------------|
| `{{tenant_name}}` | Tenant's full name |
| `{{tenant_email}}` | Tenant's email |
| `{{property_name}}` | Property name |
| `{{property_address}}` | Full property address |
| `{{unit_number}}` | Unit identifier |
| `{{monthly_rent}}` | Lease rent amount |
| `{{security_deposit}}` | Security deposit |
| `{{lease_start_date}}` | Lease start date |
| `{{lease_end_date}}` | Lease end date |
| `{{today}}` | Current date |

### Signature Tags

Add signature placeholders where signatures are needed:

```markdown
**TENANT SIGNATURE:**
[SIGNATURE:Tenant]

**LANDLORD SIGNATURE:**
[SIGNATURE:Landlord]
```

**Signature Roles:**
- `Tenant` - Primary tenant
- `Landlord` - Property manager/owner
- `Cosigner` - Co-signer on lease
- `Witness` - Witness signature
- `Occupant` - Additional occupant

### Creating an eDocument

1. Navigate to **Documents** → **eDocuments** → **Create**
2. Select a template (or create from scratch)
3. Associate with a lease (optional, auto-fills variables)
4. Review and edit content
5. Click **Save**

### Sending for Signatures

1. Open the eDocument
2. Click **Assign Signers**
3. Add signers with:
   - Name and email
   - Role (matches signature tags)
   - Signing order (sequential or parallel)
4. Click **Send for Signatures**

### Signing Process

1. Signers receive email with unique signing link
2. Links expire after 7 days (configurable)
3. Signer views the document
4. Draws signature on canvas
5. Types full name for confirmation
6. Signature recorded with timestamp and IP

### Document Status

| Status | Description |
|--------|-------------|
| Draft | Being edited, not sent |
| Pending | Sent, awaiting signatures |
| Partial | Some signatures collected |
| Completed | All signatures collected |
| Cancelled | Document cancelled |

### Viewing Signed Documents

1. Navigate to **Documents** → **eDocuments**
2. Filter by status or search
3. Click to view document with signatures
4. Download as PDF with signatures embedded

### Lease Status

| Status | Description |
|--------|-------------|
| Draft | Lease being prepared |
| Pending | Awaiting signatures/approval |
| Active | Current, valid lease |
| Expired | Past end date |
| Terminated | Ended early |

---

## Billing Configuration

### Property Billing Settings

Each property has its own billing configuration:

1. Navigate to **Properties** → Select property → **Billing Settings**
2. Configure:
   - **Late Fee Type** - Flat amount or percentage
   - **Late Fee Amount** - Dollar amount or percentage value
   - **Grace Period Days** - Days after due date before late fee
   - **Invoice Generation Day** - Day of month to generate invoices

### Late Fee Examples

**Flat Fee:**
- Late Fee Type: Flat
- Late Fee Amount: $50
- Grace Period: 5 days

Result: $50 fee applied 5 days after due date.

**Percentage Fee:**
- Late Fee Type: Percentage
- Late Fee Amount: 5%
- Grace Period: 5 days

Result: 5% of rent amount applied 5 days after due date.

---

## Invoice Management

### Automatic Invoice Generation

PropManager automatically generates invoices via background task:

1. Runs daily via Django-Q2
2. Checks for leases needing invoices
3. Creates invoices with:
   - Base rent
   - Additional fees (pet fees, parking, etc.)
   - Any credits/adjustments
4. Sends notification to tenant

### Manual Invoice Creation

1. Navigate to **Billing** → **Create Invoice**
2. Select tenant and lease
3. Add line items:
   - Description
   - Amount
   - Quantity
4. Set due date
5. Click **Create Invoice**

### Invoice Status

| Status | Description |
|--------|-------------|
| Draft | Not yet sent |
| Sent | Delivered to tenant |
| Paid | Fully paid |
| Partial | Partially paid |
| Overdue | Past due date, unpaid |
| Void | Cancelled invoice |

### Applying Late Fees

Late fees are applied automatically:

1. Daily task checks overdue invoices
2. Calculates late fee based on property settings
3. Adds late fee line item to invoice
4. Notifies tenant of additional charge

### Viewing Invoice History

- Navigate to **Billing** → **Invoices**
- Filter by:
  - Property
  - Tenant
  - Status
  - Date range
- Export to CSV for reporting

---

## Payment Processing

### Payment Gateway Setup

PropManager supports multiple payment gateways. Configure them in **Settings** → **Payment Gateways**.

#### Stripe

1. Click **Configure** next to Stripe
2. Enter:
   - **API Key** - Your Stripe secret key
   - **Publishable Key** - Your Stripe publishable key
   - **Webhook Secret** - For webhook verification
3. Enable desired payment methods (cards, ACH)
4. Click **Save**

#### PayPal

1. Click **Configure** next to PayPal
2. Enter:
   - **Client ID** - PayPal application client ID
   - **Client Secret** - PayPal application secret
   - **Sandbox Mode** - Toggle for testing
3. Click **Save**

#### Square

1. Click **Configure** next to Square
2. Enter:
   - **Access Token** - Square access token
   - **Location ID** - Square location identifier
   - **Application ID** - Square application ID
3. Click **Save**

#### Authorize.Net

1. Click **Configure** next to Authorize.Net
2. Enter:
   - **API Login ID** - Merchant API login
   - **Transaction Key** - Merchant transaction key
   - **Sandbox Mode** - Toggle for testing
3. Click **Save**

#### Braintree

1. Click **Configure** next to Braintree
2. Enter:
   - **Merchant ID** - Braintree merchant ID
   - **Public Key** - Braintree public key
   - **Private Key** - Braintree private key
   - **Environment** - Sandbox or Production
3. Click **Save**

#### Plaid ACH

1. Click **Configure** next to Plaid
2. Enter:
   - **Client ID** - Plaid client ID
   - **Secret** - Plaid secret key
   - **Environment** - Sandbox, Development, or Production
3. Click **Save**

#### Bitcoin (BTCPay Server)

1. Click **Configure** next to Bitcoin
2. Enter:
   - **BTCPay Server URL** - Your BTCPay Server instance
   - **Store ID** - BTCPay store identifier
   - **API Key** - BTCPay API key
3. Click **Save**

### Recording Manual Payments

For payments received outside the system (checks, cash):

1. Navigate to the invoice
2. Click **Record Payment**
3. Enter:
   - **Amount** - Payment amount
   - **Payment Method** - Check, cash, money order, etc.
   - **Reference Number** - Check number, receipt number
   - **Date Received** - Payment date
4. Click **Save**

### Refunds

1. Navigate to the payment
2. Click **Issue Refund**
3. Enter refund amount (partial or full)
4. Select reason
5. Click **Process Refund**

---

## Work Orders

### Viewing Work Orders

Navigate to **Work Orders** to see all maintenance requests:

- Filter by status, property, priority
- Sort by date, priority, or property
- Search by tenant or description

### Work Order Status

| Status | Description |
|--------|-------------|
| Submitted | New request from tenant |
| Acknowledged | Received and being reviewed |
| In Progress | Work has begun |
| Pending Parts | Waiting for materials |
| Completed | Work finished |
| Cancelled | Request cancelled |

### Work Order Priority

| Priority | Description |
|----------|-------------|
| Emergency | Safety issue, requires immediate attention |
| High | Important, should be addressed within 24 hours |
| Normal | Standard maintenance, within a week |
| Low | Non-urgent, can be scheduled |

### Assigning Contractors

1. Open work order detail
2. Click **Assign Contractor**
3. Select from contractor list or add new
4. Contractor receives email with access token
5. Contractor can view work order details and update status

### Contractor Token Access

Contractors access work orders via secure token links:

1. Contractor clicks link in email
2. Views work order details (no login required)
3. Can add notes and update status
4. Token expires after work completion

### Work Order Notes

Add notes to track progress:

1. Open work order detail
2. Scroll to **Notes** section
3. Enter note text
4. Click **Add Note**

Notes are timestamped and attributed to the user.

### Attachments

Tenants and staff can attach files:

- Photos of the issue
- Receipts for parts
- Completion photos
- Documents

---

## Rewards Program

### Program Overview

The tenant rewards program incentivizes on-time payments:

- **Streak Rewards** - Rewards for consecutive on-time payments
- **Prepayment Bonuses** - Rewards for paying multiple months ahead

### Configuring Rewards

1. Navigate to **Properties** → Select property → **Rewards Settings**
2. Enable the rewards program
3. Configure streak rewards:

| Milestone | Default Reward |
|-----------|----------------|
| 3-month streak | $25 credit |
| 6-month streak | $50 credit |
| 12-month streak | $100 credit |

4. Configure prepayment bonuses:

| Prepayment | Default Bonus |
|------------|---------------|
| 2 months | $15 credit |
| 3 months | $30 credit |
| 6 months | $75 credit |

5. Click **Save**

### Viewing Tenant Rewards

1. Navigate to tenant profile
2. View **Rewards** section:
   - Current points balance
   - Reward history
   - Current streak count

### Manual Reward Adjustments

1. Navigate to tenant profile → **Rewards**
2. Click **Add Adjustment**
3. Enter:
   - Points (positive or negative)
   - Reason
4. Click **Save**

---

## Communications

### Notification Groups

Create groups for targeted messaging:

1. Navigate to **Communications** → **Notification Groups**
2. Click **Create Group**
3. Enter group name and description
4. Add tenants to the group
5. Click **Save**

### Sending Messages

1. Navigate to **Communications** → **Send Message**
2. Select recipients:
   - Individual tenants
   - Notification groups
   - All tenants at a property
3. Compose message:
   - Subject
   - Body (supports formatting)
4. Select channels:
   - Email
   - SMS
   - In-App notification
5. Click **Send**

### Message Templates

Create reusable templates:

1. Navigate to **Communications** → **Templates**
2. Click **Create Template**
3. Enter:
   - Template name
   - Subject
   - Body (with placeholders)
4. Click **Save**

**Available Placeholders:**
- `{{tenant_name}}` - Tenant's full name
- `{{property_name}}` - Property name
- `{{unit_number}}` - Unit identifier
- `{{amount_due}}` - Outstanding balance
- `{{due_date}}` - Payment due date

### Notification History

View sent notifications:

1. Navigate to **Communications** → **History**
2. Filter by:
   - Date range
   - Channel (email, SMS, in-app)
   - Recipient
   - Status

---

## Weather Notifications

### Weather API Setup

1. Navigate to **Settings** → **Weather**
2. Enter OpenWeatherMap API key
3. Configure alert thresholds:
   - Temperature extremes
   - Wind speed warnings
   - Precipitation alerts
4. Click **Save**

### Automated Weather Alerts

PropManager automatically monitors weather and sends alerts:

1. Daily weather check runs via background task
2. If conditions meet thresholds, notification is triggered
3. Affected tenants receive alerts via configured channels

### Weather Alert Types

- **Extreme Heat** - High temperature warnings
- **Extreme Cold** - Freeze warnings, pipe protection reminders
- **Severe Weather** - Storm, tornado, hurricane alerts
- **Winter Weather** - Snow and ice notifications
- **Flood Warnings** - Heavy rain and flood alerts

---

## Reports

### Available Reports

Navigate to **Reports** for financial and operational reports:

#### Financial Reports

- **Income Summary** - Revenue by property/period
- **Outstanding Balances** - Unpaid invoice summary
- **Payment History** - All payments with details
- **Late Fee Report** - Applied late fees

#### Operational Reports

- **Occupancy Report** - Unit occupancy rates
- **Lease Expiration** - Upcoming expirations
- **Work Order Summary** - Maintenance activity
- **Tenant Roster** - Current tenant list

### Exporting Reports

All reports support export:

1. Generate report with desired filters
2. Click **Export**
3. Select format:
   - CSV
   - PDF
   - Excel
4. Download file

---

## Settings

### Company Settings

Configure organization-wide settings:

- **Company Name** - Displayed in portal and documents
- **Logo** - Branding for portals and emails
- **Contact Information** - Support email and phone
- **Address** - Company address

### User Management

Manage admin users:

1. Navigate to **Settings** → **Users**
2. Click **Add User**
3. Enter:
   - Email
   - Name
   - Role (Admin, Manager, Staff)
   - Properties (for property-specific access)
4. Click **Create User**

### Roles and Permissions

| Role | Permissions |
|------|-------------|
| Admin | Full access to all features |
| Manager | Property management, no system settings |
| Staff | Limited access (work orders, tenant communication) |

### Audit Log

View system activity:

1. Navigate to **Settings** → **Audit Log**
2. Filter by:
   - User
   - Action type
   - Date range
3. View details of each action

---

## Best Practices

### Daily Tasks

- [ ] Check dashboard for alerts
- [ ] Review new work orders
- [ ] Process pending payments
- [ ] Respond to tenant messages

### Weekly Tasks

- [ ] Review overdue invoices
- [ ] Check upcoming lease expirations
- [ ] Review work order backlog
- [ ] Check payment gateway status

### Monthly Tasks

- [ ] Generate financial reports
- [ ] Review occupancy rates
- [ ] Audit late fee applications
- [ ] Update property information as needed

---

## Getting Help

- **Documentation**: Browse the [docs](../index.md) folder
- **Troubleshooting**: See [troubleshooting.md](../troubleshooting.md)
- **Support**: Contact your system administrator
