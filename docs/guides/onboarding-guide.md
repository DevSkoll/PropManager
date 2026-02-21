# Tenant Onboarding Guide

This guide covers the complete tenant onboarding workflow in PropManager, from creating a lease for a new tenant to their first login.

---

## Overview

PropManager's onboarding system solves the "chicken or egg" problem between leases and tenants:

1. **Lease First** - Admin creates lease with prospective tenant info (no account required)
2. **Account During Onboarding** - Tenant creates account as part of the wizard
3. **Data Linked to Lease** - All collected info automatically links to the lease
4. **Invoices Generated** - Move-in fees become payable invoices on completion

---

## For Property Managers

### Creating a Lease for a New Tenant

1. Navigate to **Leases** → **Create Lease**
2. In the **Tenant Selection** section, choose **"New Tenant (Onboarding Required)"**
3. Enter prospective tenant info:
   - First Name (required)
   - Last Name
   - Email (required - used for invitation)
   - Phone (optional - for SMS notifications)
4. Fill in lease details: unit, rent, dates, policies
5. Click **Save Lease**

The lease is created with status "Draft" and appears in the **Pending Onboarding** section.

### Starting the Onboarding Process

1. Go to the lease detail page
2. You'll see a **"Pending Onboarding"** banner
3. Click **"Start Onboarding"**
4. Review the prospective tenant info
5. Optionally select a custom onboarding template
6. Click **"Send Onboarding Invitation"**

An email is sent to the prospective tenant with a unique link to complete onboarding.

### Monitoring Onboarding Progress

Navigate to **Onboarding** → **Sessions** to see:

- **Pending** - Invitation sent, not yet started
- **In Progress** - Tenant actively completing steps
- **Completed** - Successfully onboarded
- **Expired** - Link expired without completion
- **Cancelled** - Manually cancelled by admin

Click any session to view detailed progress, including:
- Steps completed with timestamps
- Documents signed
- Payments/fees acknowledged
- Step-by-step activity log

### Managing Onboarding Templates

Templates control which steps tenants must complete. Navigate to **Onboarding** → **Templates**.

**Available Steps:**
| Step | Description | Default |
|------|-------------|---------|
| Account Creation | Email verification + account setup | Required |
| Personal Info | DOB, SSN last 4, driver's license | Optional |
| Emergency Contacts | At least one contact | Required |
| Occupants | Household members | Optional |
| Pets | Pet registration | Optional |
| Vehicles | Vehicle registration | Optional |
| Employment | Income verification | Optional |
| Insurance | Renter's insurance | Optional |
| ID Verification | Photo ID upload | Optional |
| Documents | eDocument signing | Required |
| Fee Review | Acknowledge move-in costs | Required |
| Move-In Schedule | Select move-in date/time | Optional |
| Welcome | Property rules and info | Required |

**Template Settings:**
- Enable/disable individual steps
- Mark steps as required or optional
- Set step order
- Configure fee templates (security deposit, first month rent, etc.)
- Add document templates to sign
- Customize welcome message and property rules

### Using Onboarding Presets

PropManager includes 15 pre-built presets for common scenarios:

| Preset | Best For | Key Features |
|--------|----------|--------------|
| Standard | General apartments | Basic requirements |
| Premium | Upscale rentals | Insurance required, income verification |
| Luxury | High-end properties | Full verification, detailed ID check |
| Corporate | Business rentals | Employment focus, company billing |
| Furnished | Turnkey units | Inventory checklist |
| Short-Term | < 6 month leases | Simplified flow |
| Student | Campus housing | School verification, co-signer |
| Senior | 55+ communities | Minimal tech requirements |
| Affordable | Income-restricted | Income verification required |
| Military | Service members | BAH documentation |
| Pet-Friendly | Pet-allowed units | Pet details required |
| International | Non-US tenants | Passport/visa verification |
| Section 8 | Voucher holders | Voucher documentation |
| Co-Living | Shared spaces | Room-specific rules |
| ADA | Accessible units | Accommodation requests |

To apply a preset: **Onboarding** → **Presets** → Select → **Apply to Property**

---

## For Tenants

### Completing Your Onboarding

When you receive an onboarding invitation email:

1. **Click the link** in the email
2. **Verify your email** - Click "Send Code" to receive a 6-digit code
3. **Enter the code** - Check your email and enter the verification code
4. **Create your account** - Enter your name and contact preferences
5. **Complete each step** - Fill in the required information:
   - Personal details
   - Emergency contacts (at least one required)
   - Household members (if any)
   - Pets (if applicable)
   - Vehicles (if applicable)
   - Employment information
   - Renter's insurance
   - Sign lease documents
   - Review move-in fees
   - Schedule move-in date
6. **Welcome!** - Review property rules and complete onboarding

### What Information You'll Need

Have these ready before starting:

**Personal:**
- Date of birth
- SSN (last 4 digits only)
- Driver's license number and state

**Emergency Contact:**
- Name, phone, email
- Relationship to you

**Household Members (if any):**
- Names and dates of birth
- Relationship to you

**Pets (if any):**
- Pet type, breed, weight
- Vaccination status
- Service animal documentation (if applicable)

**Vehicles (if parking provided):**
- Make, model, year, color
- License plate and state

**Employment:**
- Employer name and contact
- Job title and start date
- Income information

**Insurance:**
- Provider name and policy number
- Coverage amounts
- Policy dates

**ID Verification:**
- Photo ID (front and back)
- Must be current/unexpired

### After Completing Onboarding

Once you complete onboarding:

1. **Your account is active** - You can log in to the tenant portal
2. **Your lease is linked** - View your lease details in the portal
3. **Invoices are ready** - Move-in fees appear in your billing
4. **Documents are saved** - Signed documents are in your document library

---

## Technical Reference

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        LEASE CREATION                            │
│  Admin creates lease with prospective_* fields, tenant=null     │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     START ONBOARDING                             │
│  OnboardingService.create_session() links session to lease      │
│  Invitation email sent to prospective_email                      │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ONBOARDING WIZARD                              │
│  Step 1: Verify email (OTP)                                      │
│  Step 2: Create account → User created, session.tenant set      │
│  Steps 3-12: Collect data → Saved to models linked to lease    │
│  Step 13: Welcome page                                           │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    COMPLETION                                    │
│  OnboardingService.complete_session():                           │
│  1. lease.tenant = session.tenant                                │
│  2. Clear prospective_* fields                                   │
│  3. Update lease.move_in_date                                    │
│  4. Transfer personal info to TenantProfile                      │
│  5. Generate invoices from template fees                         │
│  6. Send completion notifications                                │
└─────────────────────────────────────────────────────────────────┘
```

### Models Involved

| Model | App | Purpose |
|-------|-----|---------|
| `Lease` | leases | Core lease with prospective fields |
| `LeaseOccupant` | leases | Household members |
| `LeasePet` | leases | Registered pets |
| `OnboardingSession` | tenant_lifecycle | Tracks wizard progress |
| `OnboardingTemplate` | tenant_lifecycle | Step configuration |
| `OnboardingPreset` | tenant_lifecycle | Pre-built templates |
| `TenantProfile` | accounts | Personal info (DOB, SSN, etc.) |
| `TenantEmergencyContact` | tenant_lifecycle | Emergency contacts |
| `TenantVehicle` | tenant_lifecycle | Registered vehicles |
| `TenantEmployment` | tenant_lifecycle | Employment info |
| `TenantInsurance` | tenant_lifecycle | Insurance policies |
| `TenantIDVerification` | tenant_lifecycle | ID documents |

### Key URLs

| URL Pattern | View | Purpose |
|-------------|------|---------|
| `/admin-portal/leases/create/` | `admin_lease_create` | Create lease |
| `/admin-portal/leases/{pk}/start-onboarding/` | `admin_lease_start_onboarding` | Start onboarding |
| `/admin-portal/onboarding/sessions/` | `session_list` | List sessions |
| `/admin-portal/onboarding/sessions/create/` | `session_create` | Create session |
| `/admin-portal/onboarding/templates/` | `template_list` | Manage templates |
| `/admin-portal/onboarding/presets/` | `preset_list` | View presets |
| `/onboard/start/{token}/` | `onboarding_start` | Tenant entry point |

### Service Methods

**OnboardingService** (`apps/tenant_lifecycle/services.py`):

| Method | Purpose |
|--------|---------|
| `create_session()` | Create session linked to lease |
| `send_invitation()` | Send email/SMS invitation |
| `create_tenant_account()` | Create User during onboarding |
| `create_session_documents()` | Generate eDocuments from template |
| `complete_session()` | Finalize onboarding, link tenant |
| `generate_move_in_invoices()` | Create invoices from fees |
| `send_completion_notification()` | Notify tenant and admin |

---

## Troubleshooting

### Common Issues

**"Cannot create onboarding session"**
- Ensure the lease has no tenant assigned
- Verify prospective_email is set
- Check that no active session exists for the lease

**"Invalid or expired link"**
- Links expire after the configured days (default: 7)
- Resend invitation from session detail page

**"Cannot activate lease"**
- Lease requires assigned tenant to activate
- Complete onboarding first, or assign existing tenant

**OTP code not received**
- Check spam/junk folder
- Verify email address is correct
- Resend code after 60 seconds

### Getting Help

- Check the session detail page for step-by-step logs
- Review the [Troubleshooting Guide](../troubleshooting.md)
- Contact your system administrator

---

## See Also

- [Admin Guide](admin-guide.md) - Complete admin portal documentation
- [Tenant Guide](tenant-guide.md) - Tenant portal features
- [Architecture](../architecture.md) - System design details
