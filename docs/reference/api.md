# API Reference

This document provides a reference for PropManager's URL endpoints and views.

## Table of Contents

- [Overview](#overview)
- [Admin Portal URLs](#admin-portal-urls)
- [Admin API Endpoints](#admin-api-endpoints)
- [Tenant Portal URLs](#tenant-portal-urls)
- [Tenant Onboarding URLs](#tenant-onboarding-urls)
- [Public URLs](#public-urls)
- [Webhook Endpoints](#webhook-endpoints)
- [Authentication](#authentication)

---

## Overview

PropManager uses Django's URL routing system with namespaced URLs for organization.

### URL Namespaces

| Namespace | Description | Base Path |
|-----------|-------------|-----------|
| `admin_portal` | Admin portal views | `/admin-portal/` |
| `tenant` | Tenant portal views | `/tenant/` |
| `billing` | Billing views | `/billing/` |
| `billing_admin` | Admin billing views | `/admin-portal/billing/` |
| `leases` | Tenant lease views | `/tenant/leases/` |
| `leases_admin` | Admin lease views | `/admin-portal/leases/` |
| `workorders` | Work order views | `/workorders/` |
| `workorders_admin` | Admin work order views | `/admin-portal/workorders/` |
| `communications` | Communication views | `/communications/` |
| `rewards` | Rewards views | `/rewards/` |

### URL Patterns

PropManager follows RESTful conventions:

```
/resource/                  # List
/resource/create/           # Create form
/resource/<pk>/             # Detail
/resource/<pk>/edit/        # Edit form
/resource/<pk>/delete/      # Delete
```

---

## Admin Portal URLs

### Dashboard

| URL | Name | Description |
|-----|------|-------------|
| `/admin-portal/` | `admin_portal:dashboard` | Admin dashboard |

### Properties

| URL | Name | Description |
|-----|------|-------------|
| `/admin-portal/properties/` | `admin_portal:property_list` | List all properties |
| `/admin-portal/properties/create/` | `admin_portal:property_create` | Create property form |
| `/admin-portal/properties/<pk>/` | `admin_portal:property_detail` | Property details |
| `/admin-portal/properties/<pk>/edit/` | `admin_portal:property_edit` | Edit property |
| `/admin-portal/properties/<pk>/settings/` | `admin_portal:property_settings` | Property settings |

### Units

| URL | Name | Description |
|-----|------|-------------|
| `/admin-portal/properties/<pk>/units/` | `admin_portal:unit_list` | List units for property |
| `/admin-portal/units/create/` | `admin_portal:unit_create` | Create unit form |
| `/admin-portal/units/<pk>/` | `admin_portal:unit_detail` | Unit details |
| `/admin-portal/units/<pk>/edit/` | `admin_portal:unit_edit` | Edit unit |

### Tenants

| URL | Name | Description |
|-----|------|-------------|
| `/admin-portal/tenants/` | `admin_portal:tenant_list` | List all tenants |
| `/admin-portal/tenants/create/` | `admin_portal:tenant_create` | Create tenant form |
| `/admin-portal/tenants/<pk>/` | `admin_portal:tenant_detail` | Tenant details |
| `/admin-portal/tenants/<pk>/edit/` | `admin_portal:tenant_edit` | Edit tenant |

### Leases (Admin)

| URL | Name | Description |
|-----|------|-------------|
| `/admin-portal/leases/` | `leases_admin:lease_list` | List all leases |
| `/admin-portal/leases/create/` | `leases_admin:lease_create` | Create lease form |
| `/admin-portal/leases/<pk>/` | `leases_admin:lease_detail` | Lease details |
| `/admin-portal/leases/<pk>/edit/` | `leases_admin:lease_edit` | Edit lease |
| `/admin-portal/leases/<pk>/send-signature/` | `leases_admin:lease_send_signature` | Send for signatures |
| `/admin-portal/leases/<pk>/add-term/` | `leases_admin:lease_add_term` | Add lease term |
| `/admin-portal/leases/<pk>/add-occupant/` | `leases_admin:lease_add_occupant` | Add occupant |
| `/admin-portal/leases/<pk>/add-pet/` | `leases_admin:lease_add_pet` | Add pet |
| `/admin-portal/leases/<pk>/add-fee/` | `leases_admin:lease_add_fee` | Add fee |

### Billing (Admin)

| URL | Name | Description |
|-----|------|-------------|
| `/admin-portal/billing/` | `billing_admin:invoice_list` | List invoices |
| `/admin-portal/billing/invoices/` | `billing_admin:invoice_list` | List invoices |
| `/admin-portal/billing/invoices/create/` | `billing_admin:invoice_create` | Create invoice |
| `/admin-portal/billing/invoices/<pk>/` | `billing_admin:invoice_detail` | Invoice details |
| `/admin-portal/billing/payments/` | `billing_admin:payment_list` | List payments |
| `/admin-portal/billing/payments/<pk>/` | `billing_admin:payment_detail` | Payment details |
| `/admin-portal/billing/payments/record/` | `billing_admin:record_payment` | Record manual payment |

### Work Orders (Admin)

| URL | Name | Description |
|-----|------|-------------|
| `/admin-portal/workorders/` | `workorders_admin:workorder_list` | List work orders |
| `/admin-portal/workorders/<pk>/` | `workorders_admin:workorder_detail` | Work order details |
| `/admin-portal/workorders/<pk>/assign/` | `workorders_admin:workorder_assign` | Assign contractor |
| `/admin-portal/workorders/<pk>/update-status/` | `workorders_admin:workorder_status` | Update status |

### Communications (Admin)

| URL | Name | Description |
|-----|------|-------------|
| `/admin-portal/communications/` | `communications:message_list` | List messages |
| `/admin-portal/communications/send/` | `communications:send_message` | Send message form |
| `/admin-portal/communications/groups/` | `communications:group_list` | Notification groups |
| `/admin-portal/communications/groups/create/` | `communications:group_create` | Create group |
| `/admin-portal/communications/templates/` | `communications:template_list` | Message templates |

### Settings (Admin)

| URL | Name | Description |
|-----|------|-------------|
| `/admin-portal/settings/` | `admin_portal:settings` | General settings |
| `/admin-portal/settings/payment-gateways/` | `admin_portal:payment_gateways` | Payment gateway config |
| `/admin-portal/settings/users/` | `admin_portal:user_list` | User management |
| `/admin-portal/settings/weather/` | `admin_portal:weather_settings` | Weather API settings |

### Tenant Onboarding (Admin)

| URL | Name | Description |
|-----|------|-------------|
| `/admin-portal/onboarding/templates/` | `tenant_lifecycle:template_list` | List onboarding templates |
| `/admin-portal/onboarding/templates/create/` | `tenant_lifecycle:template_create` | Create onboarding template |
| `/admin-portal/onboarding/templates/<pk>/` | `tenant_lifecycle:template_detail` | Template detail |
| `/admin-portal/onboarding/templates/<pk>/edit/` | `tenant_lifecycle:template_edit` | Edit template |
| `/admin-portal/onboarding/sessions/` | `tenant_lifecycle:session_list` | List onboarding sessions |
| `/admin-portal/onboarding/sessions/create/` | `tenant_lifecycle:session_create` | Invite new tenant |
| `/admin-portal/onboarding/sessions/<pk>/` | `tenant_lifecycle:session_detail` | Session details |

### eDocuments (Admin)

| URL | Name | Description |
|-----|------|-------------|
| `/admin-portal/edocs/` | `documents_admin:edoc_list` | List eDocuments |
| `/admin-portal/edocs/create/` | `documents_admin:edoc_create` | Create eDocument |
| `/admin-portal/edocs/<pk>/` | `documents_admin:edoc_detail` | eDocument detail |
| `/admin-portal/edocs/<pk>/edit/` | `documents_admin:edoc_edit` | Edit eDocument |
| `/admin-portal/edocs/<pk>/send/` | `documents_admin:edoc_send` | Send for signatures |
| `/admin-portal/edocs/templates/` | `documents_admin:template_list` | eDocument templates |
| `/admin-portal/edocs/templates/create/` | `documents_admin:template_create` | Create template |
| `/admin-portal/edocs/templates/<pk>/` | `documents_admin:template_detail` | Template detail |

---

## Admin API Endpoints

JSON API endpoints for internal use by the admin portal.

### Global Search API

| URL | Name | Description |
|-----|------|-------------|
| `/admin-portal/api/search/` | `accounts_admin:admin_global_search` | Global search across all entities |

#### Global Search

Search across apps, tenants, properties, units, leases, documents, work orders, and invoices.

**Request:**
```
GET /admin-portal/api/search/?q=<query>&limit=<limit>
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query (min 2 characters) |
| `limit` | integer | No | Max results per category (default: 5, max: 10) |

**Response:**
```json
{
  "query": "john",
  "categories": {
    "tenants": {
      "label": "Tenants",
      "icon": "bi-people",
      "results": [
        {
          "id": "uuid",
          "title": "John Smith",
          "subtitle": "john.smith@email.com",
          "url": "/admin-portal/tenants/?q=john.smith@email.com",
          "icon": "bi-person"
        }
      ],
      "total": 3
    },
    "properties": {
      "label": "Properties",
      "icon": "bi-building",
      "results": [...],
      "total": 1
    },
    "units": {
      "label": "Units",
      "icon": "bi-door-open",
      "results": [...],
      "total": 2
    },
    "leases": {
      "label": "Leases",
      "icon": "bi-file-earmark-text",
      "results": [...],
      "total": 1
    },
    "documents": {
      "label": "Documents",
      "icon": "bi-file-earmark-pdf",
      "results": [...],
      "total": 0
    },
    "work_orders": {
      "label": "Work Orders",
      "icon": "bi-tools",
      "results": [...],
      "total": 1
    },
    "invoices": {
      "label": "Invoices",
      "icon": "bi-receipt",
      "results": [...],
      "total": 2
    }
  },
  "total_results": 10
}
```

**Search Priority Order:**
1. Apps (client-side, instant)
2. Tenants
3. Properties
4. Units
5. Leases
6. Documents
7. Work Orders
8. Invoices

**Fields Searched per Category:**

| Category | Fields |
|----------|--------|
| Tenants | first_name, last_name, email, phone_number |
| Properties | name, address_line1, city |
| Units | unit_number, property name |
| Leases | tenant name, unit number, property name |
| Documents | title, template name |
| Work Orders | title, description |
| Invoices | invoice_number, tenant name |

---

## Tenant Portal URLs

### Dashboard & Auth

| URL | Name | Description |
|-----|------|-------------|
| `/tenant/` | `tenant:dashboard` | Tenant dashboard |
| `/tenant/login/` | `tenant:login` | OTP login form |
| `/tenant/login/verify/` | `tenant:login_verify` | OTP verification |
| `/tenant/logout/` | `tenant:logout` | Logout |

### Leases (Tenant)

| URL | Name | Description |
|-----|------|-------------|
| `/tenant/leases/` | `leases:lease_list` | List tenant's leases |
| `/tenant/leases/<pk>/` | `leases:lease_detail` | Lease detail view |

### Billing (Tenant)

| URL | Name | Description |
|-----|------|-------------|
| `/tenant/billing/` | `billing:invoice_list` | List tenant's invoices |
| `/tenant/billing/invoices/<pk>/` | `billing:invoice_detail` | Invoice detail |
| `/tenant/billing/pay/` | `billing:make_payment` | Make a payment |
| `/tenant/billing/payment-methods/` | `billing:payment_methods` | Manage payment methods |
| `/tenant/billing/payment-methods/add/` | `billing:add_payment_method` | Add payment method |
| `/tenant/billing/autopay/` | `billing:autopay_settings` | AutoPay configuration |
| `/tenant/billing/history/` | `billing:payment_history` | Payment history |

### Work Orders (Tenant)

| URL | Name | Description |
|-----|------|-------------|
| `/tenant/workorders/` | `workorders:workorder_list` | List tenant's work orders |
| `/tenant/workorders/create/` | `workorders:workorder_create` | Submit work order |
| `/tenant/workorders/<pk>/` | `workorders:workorder_detail` | Work order detail |

### Documents (Tenant)

| URL | Name | Description |
|-----|------|-------------|
| `/tenant/documents/` | `tenant:document_list` | List documents |
| `/tenant/documents/<pk>/` | `tenant:document_detail` | View document |
| `/tenant/documents/<pk>/download/` | `tenant:document_download` | Download document |

### Messages (Tenant)

| URL | Name | Description |
|-----|------|-------------|
| `/tenant/messages/` | `tenant:message_list` | List messages |
| `/tenant/messages/<pk>/` | `tenant:message_detail` | View message |
| `/tenant/messages/compose/` | `tenant:message_compose` | Send message |

### Rewards (Tenant)

| URL | Name | Description |
|-----|------|-------------|
| `/tenant/rewards/` | `rewards:dashboard` | Rewards dashboard |
| `/tenant/rewards/history/` | `rewards:history` | Reward history |

### Settings (Tenant)

| URL | Name | Description |
|-----|------|-------------|
| `/tenant/settings/` | `tenant:settings` | Account settings |
| `/tenant/settings/profile/` | `tenant:profile` | Edit profile |
| `/tenant/settings/notifications/` | `tenant:notification_preferences` | Notification prefs |

---

## Tenant Onboarding URLs

Public URLs for prospective tenants completing the onboarding process.

### Onboarding Flow

| URL | Name | Description |
|-----|------|-------------|
| `/onboard/start/<token>/` | `tenant_lifecycle:onboarding_start` | Entry point, redirects to current step |
| `/onboard/<token>/verify/` | `tenant_lifecycle:onboarding_verify` | Email/phone verification |
| `/onboard/<token>/otp/` | `tenant_lifecycle:onboarding_otp` | OTP code entry |
| `/onboard/<token>/create-account/` | `tenant_lifecycle:onboarding_account` | Create tenant account |
| `/onboard/<token>/personal-info/` | `tenant_lifecycle:onboarding_personal` | Personal information |
| `/onboard/<token>/emergency-contacts/` | `tenant_lifecycle:onboarding_emergency` | Emergency contacts |
| `/onboard/<token>/occupants/` | `tenant_lifecycle:onboarding_occupants` | Additional occupants |
| `/onboard/<token>/pets/` | `tenant_lifecycle:onboarding_pets` | Pet registration |
| `/onboard/<token>/vehicles/` | `tenant_lifecycle:onboarding_vehicles` | Vehicle registration |
| `/onboard/<token>/employment/` | `tenant_lifecycle:onboarding_employment` | Employment info |
| `/onboard/<token>/insurance/` | `tenant_lifecycle:onboarding_insurance` | Renter's insurance |
| `/onboard/<token>/documents/` | `tenant_lifecycle:onboarding_documents` | Document signing |
| `/onboard/<token>/payments/` | `tenant_lifecycle:onboarding_payments` | Move-in payments |
| `/onboard/<token>/welcome/` | `tenant_lifecycle:onboarding_welcome` | Welcome/completion |
| `/onboard/<token>/complete/` | `tenant_lifecycle:onboarding_complete` | Confirmation page |

### Token-Based Access

Onboarding tokens are:
- 48-character cryptographically random strings
- Time-limited (configurable, default 14 days)
- Single-use per prospective tenant
- Tied to specific unit and lease

---

## Public URLs

### E-Signature

| URL | Name | Description |
|-----|------|-------------|
| `/signing/<token>/` | `leases:signing_page` | Lease signing page |
| `/signing/<token>/submit/` | `leases:submit_signature` | Submit signature |
| `/signing/complete/` | `leases:signing_complete` | Signing confirmation |
| `/signing/expired/` | `leases:signing_expired` | Expired link page |

### Contractor Access

| URL | Name | Description |
|-----|------|-------------|
| `/contractor/workorder/<token>/` | `workorders:contractor_view` | View work order |
| `/contractor/workorder/<token>/update/` | `workorders:contractor_update` | Update work order |

### OTP Login

| URL | Name | Description |
|-----|------|-------------|
| `/auth/otp/<token>/` | `core:otp_login` | OTP magic link login |

---

## Webhook Endpoints

Payment gateway webhooks for processing callbacks:

| URL | Name | Description |
|-----|------|-------------|
| `/webhooks/stripe/` | `webhooks:stripe` | Stripe webhook |
| `/webhooks/paypal/` | `webhooks:paypal` | PayPal webhook |
| `/webhooks/square/` | `webhooks:square` | Square webhook |
| `/webhooks/authorize/` | `webhooks:authorize` | Authorize.Net webhook |
| `/webhooks/braintree/` | `webhooks:braintree` | Braintree webhook |
| `/webhooks/plaid/` | `webhooks:plaid` | Plaid webhook |
| `/webhooks/btcpay/` | `webhooks:btcpay` | BTCPay Server webhook |

### Webhook Security

All webhooks implement signature verification:

```python
# Example: Stripe webhook verification
import stripe

def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    # Process event
    return HttpResponse(status=200)
```

---

## Authentication

### Tenant Authentication

Tenants use OTP (One-Time Password) authentication:

1. **Request OTP** - POST to `/tenant/login/`
   - Body: `{"email": "tenant@example.com"}`
   - Response: 200 OK, email sent

2. **Verify OTP** - Click magic link in email
   - URL: `/auth/otp/<token>/`
   - Creates session, redirects to dashboard

3. **Session** - Standard Django session
   - Cookie-based authentication
   - Configurable expiration

### Admin Authentication

Admin users use standard Django authentication:

1. **Login** - POST to `/admin-portal/login/`
   - Body: `{"username": "...", "password": "..."}`
   - Creates session

2. **Session** - Django session with staff check

### Token-Based Access

Contractors and signers use token-based access:

- **Signature tokens**: `/signing/<token>/`
- **Contractor tokens**: `/contractor/workorder/<token>/`

Tokens are:
- Cryptographically random
- Time-limited
- Single-use or limited-use
- Tied to specific resources

---

## URL Reverse Examples

Using Django's URL reversing:

```python
from django.urls import reverse

# Admin portal
reverse('admin_portal:dashboard')
reverse('admin_portal:property_detail', kwargs={'pk': 1})

# Tenant portal
reverse('tenant:dashboard')
reverse('billing:invoice_detail', kwargs={'pk': 123})

# With namespaces
reverse('leases_admin:lease_send_signature', kwargs={'pk': 1})
```

In templates:

```django
{% url 'admin_portal:dashboard' %}
{% url 'billing:invoice_detail' pk=invoice.pk %}
{% url 'leases_admin:lease_detail' pk=lease.pk %}
```

---

## Response Formats

### HTML Views

Most views return HTML responses for browser rendering.

### JSON Responses

Some views support JSON for AJAX:

```python
# Check for AJAX request
if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
    return JsonResponse({'status': 'success', 'data': ...})
```

### File Downloads

Document downloads return file responses:

```python
response = FileResponse(document.file)
response['Content-Disposition'] = f'attachment; filename="{document.name}"'
return response
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Successful request |
| 201 | Created | Resource created |
| 302 | Found | Redirect after form |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Not logged in |
| 403 | Forbidden | No permission |
| 404 | Not Found | Resource doesn't exist |
| 500 | Server Error | Unexpected error |

### Error Pages

Custom error templates:
- `templates/404.html`
- `templates/500.html`
- `templates/403.html`

---

## Further Reading

- [Management Commands](commands.md)
- [Architecture](../architecture.md)
- [Services](../services.md)
