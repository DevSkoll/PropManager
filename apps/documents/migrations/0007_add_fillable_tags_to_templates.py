"""
Data migration to update eDocument templates with fillable tags.

Adds [FILLABLE:Landlord] and [FILLABLE:Tenant] tags to appropriate templates
for dynamic content that signers can fill in during the signing process.
"""

from django.db import migrations


# Template content updates with fillable tags
UPDATES = {
    "Pet Addendum": {
        "old": """| Pet # | Type | Breed | Name | Color | Weight | Age |
|-------|------|-------|------|-------|--------|-----|
| 1 | _____ | _____ | _____ | _____ | _____ lbs | _____ |
| 2 | _____ | _____ | _____ | _____ | _____ lbs | _____ |""",
        "new": """| Pet # | Type | Breed | Name | Color | Weight | Age |
|-------|------|-------|------|-------|--------|-----|
| 1 | [FILLABLE:Tenant] | [FILLABLE:Tenant] | [FILLABLE:Tenant] | [FILLABLE:Tenant] | [FILLABLE:Tenant] lbs | [FILLABLE:Tenant] |
| 2 | [FILLABLE:Tenant] | [FILLABLE:Tenant] | [FILLABLE:Tenant] | [FILLABLE:Tenant] | [FILLABLE:Tenant] lbs | [FILLABLE:Tenant] |""",
    },
    "Parking Addendum": {
        "old": """| Vehicle # | Make | Model | Year | Color | License Plate | State |
|-----------|------|-------|------|-------|---------------|-------|
| 1 | _____ | _____ | _____ | _____ | _____ | _____ |
| 2 | _____ | _____ | _____ | _____ | _____ | _____ |""",
        "new": """| Vehicle # | Make | Model | Year | Color | License Plate | State |
|-----------|------|-------|------|-------|---------------|-------|
| 1 | [FILLABLE:Tenant] | [FILLABLE:Tenant] | [FILLABLE:Tenant] | [FILLABLE:Tenant] | [FILLABLE:Tenant] | [FILLABLE:Tenant] |
| 2 | [FILLABLE:Tenant] | [FILLABLE:Tenant] | [FILLABLE:Tenant] | [FILLABLE:Tenant] | [FILLABLE:Tenant] | [FILLABLE:Tenant] |""",
    },
    "Guarantor / Co-Signer Agreement": {
        "old": """**GUARANTOR:** _________________________________ ("Guarantor")""",
        "new": """**GUARANTOR:** [FILLABLE:Cosigner] ("Guarantor")""",
    },
    "Lease Renewal Agreement": {
        "old": """**Additional modifications (if any):**

_________________________________________________________________

_________________________________________________________________""",
        "new": """**Additional modifications (if any):**

[FILLABLE:Landlord]""",
    },
    "Notice of Entry": {
        "old": """## DESCRIPTION OF WORK/ACTIVITY

_________________________________________________________________

_________________________________________________________________

_________________________________________________________________""",
        "new": """## DESCRIPTION OF WORK/ACTIVITY

[FILLABLE:Landlord]""",
    },
}


def update_templates(apps, schema_editor):
    """Update templates with fillable tags."""
    EDocumentTemplate = apps.get_model("documents", "EDocumentTemplate")

    for template_name, changes in UPDATES.items():
        try:
            template = EDocumentTemplate.objects.get(name=template_name)
            if changes["old"] in template.content:
                template.content = template.content.replace(
                    changes["old"], changes["new"]
                )
                template.save(update_fields=["content"])
        except EDocumentTemplate.DoesNotExist:
            pass  # Template doesn't exist yet, skip


def revert_templates(apps, schema_editor):
    """Revert templates to original content."""
    EDocumentTemplate = apps.get_model("documents", "EDocumentTemplate")

    for template_name, changes in UPDATES.items():
        try:
            template = EDocumentTemplate.objects.get(name=template_name)
            if changes["new"] in template.content:
                template.content = template.content.replace(
                    changes["new"], changes["old"]
                )
                template.save(update_fields=["content"])
        except EDocumentTemplate.DoesNotExist:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0006_add_edocument_fillable_block"),
    ]

    operations = [
        migrations.RunPython(update_templates, revert_templates),
    ]
