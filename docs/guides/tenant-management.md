# Tenant Management Guide

Complete guide to managing tenants in PropManager, including viewing tenant details, archiving, restoring, and deleting tenants.

---

## Table of Contents

- [Tenant List](#tenant-list)
- [Tenant Detail Modal](#tenant-detail-modal)
- [Archiving Tenants](#archiving-tenants)
- [Restoring Tenants](#restoring-tenants)
- [Deleting Tenants](#deleting-tenants)
- [Tenant Lifecycle States](#tenant-lifecycle-states)

---

## Tenant List

Access the tenant list from **Admin Portal > Tenants** (`/admin-portal/tenants/`).

### List Features

- **Status Filter Tabs**: Switch between Active, Archived, and All tenants
- **Search**: Find tenants by name, email, or phone number
- **Click-to-View**: Click any tenant row to open the detail modal
- **Quick Actions**: Archive/Restore and Delete buttons available on each row

### Tenant Row Information

Each tenant row displays:
- Full name (or username if no name set)
- Email address
- Phone number (if provided)
- Current unit and property (if active lease)
- Account status badge (Active/Archived)
- Delete indicator (trash icon if tenant can be deleted)

---

## Tenant Detail Modal

Click any tenant row to open the tenant detail modal with complete tenant information organized across four tabs.

### Overview Tab

**Profile Information**:
- Date of birth
- Move-in date
- Driver's license (state and number)
- Email verification status
- Phone verification status
- Contact preference (email/SMS/phone)

**Current Lease**:
- Property and unit
- Monthly rent amount
- Lease dates (start/end)
- Lease status badge

**Emergency Contacts**:
- Contact name and relationship
- Phone number and email

**Registered Vehicles**:
- Year, make, model
- Color
- License plate and state

### Leases Tab

Complete lease history for the tenant:
- Property and unit
- Lease dates
- Monthly rent amount
- Lease status
- Link to full lease detail page

### Billing Tab

**Recent Invoices**:
- Invoice number with link to detail
- Issue date
- Total amount
- Payment status

**Recent Payments**:
- Payment date
- Payment method
- Amount
- Payment status

### Activity Tab

**Work Orders**:
- Work order title with link
- Status badge
- Creation date

**Onboarding Sessions**:
- Associated unit
- Session status
- Creation date

---

## Archiving Tenants

Archiving is a **soft-delete** that deactivates a tenant's account without removing any data.

### When to Archive

Archive tenants who:
- Have moved out but you want to retain their history
- Are temporarily inactive but may return
- Should no longer have system access but have billing/lease history

### How to Archive

1. From tenant list or detail modal, click **Archive** button
2. Confirm the action in the dialog
3. Tenant account is immediately deactivated

### What Happens When Archiving

- `User.is_active` is set to `False`
- Tenant can no longer log in to the tenant portal
- Tenant appears in the "Archived" tab instead of "Active"
- **All data is preserved**: leases, payments, work orders, documents, etc.
- Tenant record remains searchable for admin users

### Archive Confirmation Dialog

The system prompts:
> "Archive this tenant? They will be hidden from the active list and unable to log in."

---

## Restoring Tenants

Restoring reactivates an archived tenant's account.

### How to Restore

1. Click the **Archived** tab in the tenant list
2. Find the tenant you want to restore
3. Click **Restore** button
4. Tenant is immediately reactivated

### What Happens When Restoring

- `User.is_active` is set to `True`
- Tenant can log in to the tenant portal again
- Tenant moves from "Archived" tab to "Active" tab
- All historical data remains intact

---

## Deleting Tenants

Deletion is **permanent** and irreversible. Tenants can only be deleted if they have no critical dependencies.

### Delete Blockers

Tenants **cannot** be deleted if they have:
- Active leases (`status="active"`)
- Unpaid invoices
- Payments on record
- Work orders
- Lease history

### Who Can Be Deleted

Tenants can only be deleted if:
- They have **no active lease**
- They have **no billing history** (invoices or payments)
- They have **no work orders**
- They have **no historical leases**

Essentially, only newly created tenant accounts with zero activity can be deleted.

### How to Delete

1. From tenant list or detail modal, ensure tenant meets deletion criteria
2. Click **Delete** button (only visible if tenant can be deleted)
3. Review the deletion summary showing what will be deleted
4. Click **Delete Permanently** to confirm

### Delete Confirmation

The modal shows exactly what will be deleted:
- User account and profile
- Emergency contacts
- Vehicles
- Employment records
- Insurance policies
- ID verifications
- Onboarding sessions
- Notifications

**Warning displayed**:
> "This action cannot be undone."

### What Happens When Deleting

All related records are **permanently deleted** via cascading deletion:
- `User` record removed from database
- `TenantProfile` deleted
- `EmergencyContact` records deleted
- `Vehicle` records deleted
- `EmploymentRecord` deleted
- `TenantInsurance` deleted
- `TenantIDVerification` deleted
- `OnboardingSession` deleted
- `Notification` records deleted

---

## Tenant Lifecycle States

### State Diagram

```
┌─────────────┐
│   Active    │ ←──────────────┐
│ (is_active) │                │
└──────┬──────┘                │
       │                       │
       │ Archive               │ Restore
       │                       │
       ▼                       │
┌─────────────┐                │
│  Archived   │ ───────────────┘
│(!is_active) │
└──────┬──────┘
       │
       │ Delete (if no dependencies)
       │
       ▼
┌─────────────┐
│   DELETED   │
│ (permanent) │
└─────────────┘
```

### State Rules

| State | Can Log In? | Visible in Active List? | Can Archive? | Can Delete? |
|-------|-------------|-------------------------|--------------|-------------|
| Active | Yes | Yes | Yes | Only if no dependencies |
| Archived | No | No (in Archived tab) | N/A | Only if no dependencies |
| Deleted | N/A | No | N/A | N/A |

---

## Best Practices

### When to Archive vs Delete

**Archive** when:
- Tenant has moved out but has lease/payment history
- You want to preserve tenant data for reporting
- Tenant might return in the future
- You need to maintain audit trail

**Delete** when:
- Tenant account was created by mistake
- Duplicate account with no activity
- Test account used during onboarding
- Prospective tenant who never moved in

### Data Retention

**Recommended approach**:
1. Never delete tenants with any historical activity
2. Archive tenants when they move out
3. Keep archived tenants indefinitely for reporting and compliance
4. Only delete obvious errors (duplicate accounts, test data, etc.)

### Compliance Notes

Depending on your jurisdiction, you may be legally required to retain tenant records for a certain period. **Archiving** allows you to maintain compliance while removing active access.

Always consult local landlord-tenant laws before permanently deleting tenant data.

---

## Technical Implementation

### Database Structure

**Tenant Deletion Safety**:
- Leases: `ON DELETE PROTECT` - prevents deletion
- Invoices: `ON DELETE PROTECT` - prevents deletion
- Payments: `ON DELETE PROTECT` - prevents deletion
- Work Orders: `ON DELETE PROTECT` - prevents deletion

**Cascading Deletions** (personal data only):
- Emergency contacts, vehicles, employment records
- Insurance, ID verification
- Onboarding sessions
- Notifications

### Delete Checking

The system performs multi-stage validation:

1. **Check active lease**: `lease.status == "active"`
2. **Check invoices**: `Invoice.objects.filter(tenant=user).exists()`
3. **Check payments**: `Payment.objects.filter(tenant=user).exists()`
4. **Check work orders**: `WorkOrder.objects.filter(tenant=user).exists()`
5. **Check lease history**: `Lease.objects.filter(tenant=user).exists()`

If any check fails, delete button is disabled and blockers are displayed.

### Archive Implementation

**Soft-delete approach**:
```python
user.is_active = False
user.save(update_fields=['is_active'])
```

**Restore**:
```python
user.is_active = True
user.save(update_fields=['is_active'])
```

---

## Troubleshooting

### "Cannot delete tenant" Error

**Cause**: Tenant has dependencies (leases, invoices, etc.)

**Solution**: Archive the tenant instead of deleting. If deletion is absolutely necessary, manually remove dependencies first (not recommended).

### Tenant Still Appears in Active List After Archive

**Cause**: Browser cache or page not refreshed

**Solution**: Hard refresh the page (Ctrl+F5 or Cmd+Shift+R)

### Deleted Tenant's Data Still Visible

**Cause**: Related records weren't properly cascaded (database constraint issue)

**Solution**: Check database constraints. Run `python manage.py check` to verify model relationships.

---

## Related Documentation

- [Admin Portal Guide](admin-guide.md) - Complete admin features
- [Lease Management](lease-management.md) - Creating and managing leases
- [Tenant Onboarding](tenant-onboarding.md) - Onboarding new tenants
