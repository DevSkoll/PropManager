# Lease Documents Guide

Complete guide to linking and managing documents associated with leases in PropManager, including uploading new documents, linking existing documents, and tenant access.

---

## Table of Contents

- [Overview](#overview)
- [Admin Features](#admin-features)
  - [Viewing Lease Documents](#viewing-lease-documents)
  - [Uploading Documents](#uploading-documents)
  - [Linking Existing Documents](#linking-existing-documents)
  - [Unlinking Documents](#unlinking-documents)
- [Tenant Features](#tenant-features)
- [Automatic Document Linking](#automatic-document-linking)
- [Document Types](#document-types)
- [Best Practices](#best-practices)

---

## Overview

PropManager's lease-document system provides a centralized way to associate documents with leases, making it easy for admins to organize lease-related files and for tenants to access important documents.

### Key Concepts

- **Documents**: Physical or uploaded files (PDFs, images, etc.)
- **eDocuments**: Electronically signed documents created from markdown templates
- **Lease Linking**: Associating documents with specific leases for organization
- **Auto-Linking**: Documents uploaded during onboarding are automatically linked to the lease

### Benefits

- **Centralized Storage**: All lease-related documents in one place
- **Easy Tenant Access**: Tenants can download their lease documents from their portal
- **Automatic Organization**: Onboarding documents automatically linked during tenant move-in
- **Audit Trail**: Track what documents are associated with each lease

---

## Admin Features

Access lease documents from **Admin Portal > Leases > [Select Lease]**.

### Viewing Lease Documents

The **Lease Documents** section appears on the lease detail page with:

**Signed eDocuments** (shown first):
- Document title
- Signed date
- Download button
- Unlink button

**Uploaded Documents**:
- Document title
- Document type (insurance, photo, etc.)
- Upload date
- Download button
- Unlink button

**Empty State**:
> "No documents linked to this lease."

---

### Uploading Documents

Upload new documents directly from the lease detail page.

#### How to Upload

1. Navigate to lease detail page
2. Click **Upload** button in Lease Documents section
3. Fill out upload form:
   - **Title** (required): Descriptive name for the document
   - **Document Type**: Select from dropdown (lease, notice, inspection, receipt, insurance, photo, other)
   - **File** (required): Upload file (max 10MB)
   - **Description** (optional): Additional notes
   - **Visible to tenant**: Check to allow tenant to see/download
4. Click **Upload**

#### What Happens

- Document is uploaded to `documents/YYYY/MM/` directory
- Document record is created in the database
- Document is automatically linked to:
  - **Lease**: The current lease
  - **Unit**: The lease's unit
  - **Property**: The unit's property
  - **Tenant**: The lease's tenant
- File metadata is captured (size, MIME type)
- `uploaded_by_role` is set to "admin"
- Success message: `Document "[title]" uploaded and linked to lease.`

#### Supported File Types

- **PDFs**: `.pdf`
- **Images**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`
- **Office Docs**: `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`
- **Text**: `.txt`, `.csv`
- **Maximum size**: 10 MB per file

---

### Linking Existing Documents

Link documents that already exist in the system to the lease.

#### How to Link

1. Navigate to lease detail page
2. Click **Link** button in Lease Documents section
3. Browse available documents:
   - **Signed eDocuments tab**: Shows completed eDocuments from the unit
   - **Uploaded Documents tab**: Shows uploaded documents from the unit
4. Check the boxes for documents you want to link
5. Click **Link Selected**

#### Available Documents

The link modal shows:
- **Signed eDocuments**: All completed eDocuments from leases on the same unit that aren't already linked to this lease
- **Uploaded Documents**: All documents associated with the unit that aren't already linked to this lease

Documents already linked to the current lease do not appear in the modal.

#### Linking Multiple Documents

You can select and link multiple documents at once:
- Check multiple boxes before clicking **Link Selected**
- Success message shows count: `5 document(s) linked to lease.`

---

### Unlinking Documents

Remove the association between a document and a lease. **This does not delete the document** — it only removes the lease link.

#### How to Unlink

1. Find the document in the Lease Documents section
2. Click the **Unlink** button (red X icon)
3. Confirm: "Unlink this document from the lease?"
4. Document is removed from the lease's document list

#### What Happens

- `document.lease` field is set to `None`
- Document remains in the system and can be linked to other leases
- Document still appears in unit's document list
- Success message: `Document "[title]" unlinked from lease.`

---

## Tenant Features

Tenants can view and download lease-related documents from their portal.

### Accessing Lease Documents

1. Log in to **Tenant Portal**
2. Navigate to **My Lease** or select lease from list
3. Scroll to **Lease Documents** section

### What Tenants See

**Signed eDocuments**:
- Document title
- "Signed [date]" timestamp
- Download button (downloads final PDF)

**Uploaded Documents**:
- Document title
- Document type and upload date
- Download button

### Tenant Visibility Control

Admins control document visibility via the `is_tenant_visible` checkbox:
- **Checked**: Tenant can see and download the document
- **Unchecked**: Document hidden from tenant portal (admin-only)

**Default**: New uploads default to `is_tenant_visible=True`

### Security

- Tenants can only access documents for their own leases
- Download URLs include authentication checks
- Document downloads are logged for audit trail

---

## Automatic Document Linking

Documents uploaded during the onboarding process are automatically linked to the lease.

### Auto-Linked Documents

**During onboarding, these documents are auto-linked:**

1. **Insurance Policy Documents**
   - Uploaded in "Insurance" step
   - Title: `Insurance Policy - [Provider Name]`
   - Type: `insurance`
   - Description includes policy number and dates

2. **ID Verification Images**
   - Uploaded in "ID Verification" step
   - Title: `[ID Type] - Front` and `[ID Type] - Back`
   - Type: `photo`
   - Both front and back images linked separately

3. **Signed eDocuments**
   - Created during "Document Signing" step
   - Title: `Signed: [Document Title]`
   - Type: `lease`
   - Final PDF automatically generated and linked
   - Marked as locked (cannot be edited)

### Onboarding Folder

All auto-linked onboarding documents are also saved to an **"Onboarding"** folder for the unit:
- Folder is created automatically during first upload
- Visible to both admin and tenant
- Description: "Documents uploaded during tenant onboarding"

### When Auto-Linking Happens

- **Insurance**: Immediately after policy document upload in onboarding
- **ID Verification**: Immediately after front/back image upload
- **eDocuments**: When all required signatures are collected and document is marked complete

### Idempotent Design

Documents are only created once, even if the onboarding step is repeated:
- System checks for existing documents by file path
- Duplicate document creation is prevented
- Safe to re-run onboarding steps without creating duplicates

---

## Document Types

### Standard Document Types

| Type | Description | Common Use Cases |
|------|-------------|------------------|
| `lease` | Lease Agreement | Signed lease, lease addendums, lease renewals |
| `notice` | Notice | Move-out notice, lease violation, rent increase notice |
| `inspection` | Inspection Report | Move-in inspection, annual inspection, move-out inspection |
| `receipt` | Receipt | Rent receipt, security deposit receipt, fee receipt |
| `insurance` | Insurance | Renter's insurance policy, liability coverage proof |
| `photo` | Photo | ID verification, property photos, damage documentation |
| `other` | Other | Any document that doesn't fit other categories |

### Type Selection

- Document type is selected during upload
- Type affects icon display in document lists
- Type used for filtering and reporting
- Default type: `other`

---

## Best Practices

### Document Organization

**Keep lease documents organized**:
1. Upload all lease-related documents at lease creation
2. Link signed lease agreements immediately
3. Link renter's insurance as soon as received
4. Link move-in inspection reports
5. Link any addendums or lease modifications

### Naming Conventions

**Use clear, descriptive titles**:
- ✅ Good: "Lease Agreement - 123 Main St #101 - 2026"
- ✅ Good: "Move-In Inspection - Unit 101 - Jan 15 2026"
- ❌ Bad: "document.pdf"
- ❌ Bad: "scan_001.jpg"

### Tenant Visibility

**Make these documents tenant-visible**:
- Signed lease agreements
- Move-in inspection reports
- Lease addendums and modifications
- Pet agreements
- Parking permits
- Renter's insurance documentation

**Keep these admin-only**:
- Internal notes
- Background check results
- Credit reports
- Sensitive financial information

### Document Retention

**Recommended retention periods**:
- **Lease agreements**: Keep for 7 years after lease end
- **Move-in/Move-out inspections**: Keep for 5 years
- **Security deposit records**: Keep for 5 years
- **Rent receipts**: Keep for 7 years
- **Insurance certificates**: Keep for duration of lease + 1 year

---

## Technical Implementation

### Database Relationships

**Document model**:
```python
lease = ForeignKey('leases.Lease', related_name='documents')
unit = ForeignKey('properties.Unit', related_name='documents')
property = ForeignKey('properties.Property', related_name='documents')
tenant = ForeignKey('accounts.User', related_name='documents')
```

**EDocument model**:
```python
lease = ForeignKey('leases.Lease', related_name='edocuments')
tenant = ForeignKey('accounts.User', related_name='edocuments_received')
```

### URL Patterns

| Action | URL Pattern | View |
|--------|-------------|------|
| Upload document | `/admin-portal/leases/<uuid>/documents/upload/` | `lease_upload_document` |
| Get available docs | `/admin-portal/leases/<uuid>/documents/available/` | `lease_available_documents` |
| Link document | `/admin-portal/leases/<uuid>/documents/link/` | `lease_link_document` |
| Unlink document | `/admin-portal/leases/<uuid>/documents/unlink/` | `lease_unlink_document` |
| Link multiple | `/admin-portal/leases/<uuid>/documents/link-multiple/` | `lease_link_multiple_documents` |

### File Storage

**Upload paths**:
- Documents: `media/documents/YYYY/MM/filename.ext`
- ID verification: `media/id_verification/YYYY/MM/filename.ext`
- Insurance: `media/tenant_insurance/YYYY/MM/filename.ext`
- eDocuments: `media/edocuments/signed/YYYY/MM/filename.pdf`

**File metadata**:
- `file_size`: Stored in bytes
- `mime_type`: Auto-detected from file extension
- `uploaded_by_role`: "admin" or "tenant"

---

## Troubleshooting

### Documents Not Appearing

**Issue**: Document uploaded but not visible on lease page

**Possible causes**:
- Document not linked to lease (check link status)
- Browser cache (hard refresh: Ctrl+F5)
- Tenant visibility off (for tenant portal)

**Solution**:
- Verify document is linked by checking lease document list
- Click "Link" to re-link if needed

### Upload Fails

**Issue**: "File upload failed" error

**Possible causes**:
- File too large (>10MB)
- Unsupported file type
- Disk space full on server

**Solution**:
- Compress large PDFs
- Convert to supported format
- Check server disk space

### Tenant Can't Download Document

**Issue**: Tenant clicks download but gets error

**Possible causes**:
- `is_tenant_visible` is unchecked
- File doesn't exist on disk
- Permissions issue on media directory

**Solution**:
- Edit document and check "Visible to tenant"
- Verify file exists in media directory
- Check file permissions (should be readable by web server)

---

## Related Documentation

- [Document Management](document-management.md) - Complete document system guide
- [Tenant Onboarding](tenant-onboarding.md) - Onboarding process with auto-linking
- [eDocument System](edocuments.md) - Electronic signature workflow
- [Admin Portal Guide](admin-guide.md) - Complete admin features
