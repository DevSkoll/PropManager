"""
Data migration to seed the Residential Lease Agreement template.
"""

from django.db import migrations


LEASE_TEMPLATE_CONTENT = """# RESIDENTIAL LEASE AGREEMENT

This Residential Lease Agreement ("Lease") is entered into on {{current_date}} between:

**LANDLORD:** {{landlord_name}}
**TENANT(S):** {{tenant_name}}

The parties agree to lease the property described below under the following terms and conditions.

---

## 1. IDENTIFICATION OF PREMISES

**Property Address:** {{property_address}}
**Unit Number:** {{unit_number}}

The Premises includes the dwelling unit and any common areas or amenities that are part of the property.

---

## 2. TERM OF TENANCY

**Lease Type:** {{lease_type}}
**Start Date:** {{lease_start_date}}
**End Date:** {{lease_end_date}}

If this is a fixed-term lease, the tenancy shall automatically convert to a month-to-month tenancy at the end of the initial term unless either party provides written notice of termination at least 30 days prior to the end of the term or any renewal period.

---

## 3. RENT

**Monthly Rent:** {{monthly_rent}}
**Due Date:** Rent is due on the {{rent_due_day}} day of each month.
**Payment Methods:** Acceptable payment methods include check, money order, or electronic payment through approved channels.

Rent must be paid in full. Partial payments may be refused. Acceptance of partial payment does not waive the right to collect the full amount due.

---

## 4. LATE FEES AND GRACE PERIOD

**Grace Period:** Rent paid after the {{rent_due_day}} day of the month is subject to late fees after a {{grace_period_days}}-day grace period.
**Late Fee:** {{late_fee_amount}}

Continued late payment of rent constitutes a material breach of this Lease and may result in termination proceedings.

---

## 5. SECURITY DEPOSIT

**Security Deposit Amount:** {{security_deposit}}

The security deposit will be held by Landlord as security for the faithful performance of Tenant's obligations. The deposit may be applied to:

- Unpaid rent or late fees
- Repair of damages beyond normal wear and tear
- Cleaning costs if the unit is not left in the same condition as at move-in
- Any other amounts owed under this Lease

The security deposit or the balance thereof shall be returned within 14 days after termination of the tenancy and delivery of possession, along with an itemized statement of any deductions.

---

## 6. OCCUPANTS

**Maximum Occupants:** {{max_occupants}}
**Additional Occupants:** {{all_occupant_names}}

Only the persons listed above may reside in the Premises. Guests may stay for no more than 14 consecutive days or 30 days total in any 12-month period without Landlord's prior written consent.

---

## 7. UTILITIES AND SERVICES

**Utilities Included:** {{utilities_included}}

Tenant is responsible for all utilities and services not listed above. Tenant shall establish accounts in Tenant's name for all utilities that are Tenant's responsibility. Tenant shall not allow utilities to be disconnected during the term of this Lease.

---

## 8. PARKING

**Parking Spaces:** {{parking_spaces}}
**Assigned Space(s):** {{parking_space_numbers}}

Parking is provided solely for vehicles registered to occupants. No commercial vehicles, boats, trailers, recreational vehicles, or inoperable vehicles may be parked on the property without Landlord's prior written consent.

---

## 9. PETS

**Pets Allowed:** {{pets_allowed}}
**Maximum Pets:** {{max_pets}}

If pets are allowed, Tenant must sign a separate Pet Addendum and pay any required pet deposit or pet rent. Tenant is responsible for all damage caused by pets and must clean up after pets immediately. Pets must not disturb neighbors or create a nuisance.

---

## 10. SMOKING

**Smoking Permitted:** {{smoking_allowed}}

If smoking is not permitted, this prohibition includes cigarettes, cigars, pipes, e-cigarettes, vaping devices, and all other smoking materials. This prohibition applies to the entire Premises including balconies, patios, and within 25 feet of windows and doors.

---

## 11. QUIET ENJOYMENT

Tenant, upon paying rent and performing all terms of this Lease, shall peacefully and quietly enjoy the Premises. Tenant shall not use the Premises in any manner that violates any law or ordinance, causes damage to the Premises, or interferes with the quiet enjoyment of other tenants.

---

## 12. MAINTENANCE AND REPAIRS

**Landlord Responsibilities:**
- Maintain the structural components of the building
- Keep common areas clean and safe
- Maintain plumbing, heating, and electrical systems in working order
- Comply with all applicable building and housing codes

**Tenant Responsibilities:**
- Keep the Premises clean and sanitary
- Dispose of garbage properly
- Use all fixtures and appliances in a reasonable manner
- Report any needed repairs promptly
- Not make alterations without written consent

Tenant shall be responsible for the cost of repairs for damage caused by Tenant, occupants, or guests.

---

## 13. ENTRY BY LANDLORD

Landlord may enter the Premises:
- In case of emergency, at any time
- To make repairs, inspections, or show the Premises, with at least 24 hours' notice
- If Tenant abandons or surrenders the Premises

Landlord shall make reasonable efforts to schedule entry at times convenient to Tenant.

---

## 14. ASSIGNMENT AND SUBLETTING

Tenant shall not assign this Lease or sublet all or any portion of the Premises without the prior written consent of Landlord. Any assignment or subletting without consent shall be void and constitute a breach of this Lease.

---

## 15. CONDITION OF PREMISES

Tenant acknowledges that Tenant has inspected the Premises and accepts the Premises in their current condition, except as noted in any move-in inspection report. Tenant shall return the Premises to Landlord at the end of the tenancy in the same condition as received, reasonable wear and tear excepted.

---

## 16. RENTER'S INSURANCE

Tenant is strongly encouraged to obtain renter's insurance to protect personal belongings. Landlord's insurance does not cover Tenant's personal property or liability. Landlord shall not be liable for any loss or damage to Tenant's property regardless of cause.

---

## 17. DEFAULT AND TERMINATION

If Tenant fails to pay rent when due or violates any other term of this Lease, Landlord may:
- Demand performance or cure of the violation
- Terminate the tenancy upon proper notice as required by law
- Pursue any other remedies available under law

Tenant may terminate a month-to-month tenancy by providing at least 30 days' written notice.

---

## 18. NOTICES

All notices required under this Lease shall be in writing and delivered:
- In person
- By certified mail, return receipt requested
- By posting on the Premises if personal delivery is not possible

**Landlord's Address:**
{{office_address}}

**Tenant's Address:**
{{property_address}}, Unit {{unit_number}}

---

## 19. LEAD-BASED PAINT DISCLOSURE

For properties built before 1978: Tenant has received the federally required Lead-Based Paint Disclosure and the EPA pamphlet "Protect Your Family From Lead in Your Home."

---

## 20. MOLD PREVENTION

Tenant agrees to maintain adequate ventilation and heating to prevent mold growth and to promptly report any water intrusion, leaks, or signs of mold to Landlord. Tenant shall keep the Premises reasonably free of moisture by using exhaust fans and wiping down wet surfaces.

---

## 21. CRIME-FREE HOUSING

Tenant, members of the household, guests, and any other person under Tenant's control shall not engage in criminal activity on or near the Premises. A single violation of this provision shall be grounds for termination of the tenancy.

---

## 22. ENTIRE AGREEMENT

This Lease constitutes the entire agreement between the parties. No oral agreements or representations shall be binding unless incorporated into this Lease in writing.

---

## 23. SEVERABILITY

If any provision of this Lease is found to be invalid or unenforceable, the remaining provisions shall continue in full force and effect.

---

## 24. GOVERNING LAW

This Lease shall be governed by and construed in accordance with the laws of the State of {{property_state}}.

---

## SIGNATURES

By signing below, the parties acknowledge that they have read, understand, and agree to be bound by all terms and conditions of this Lease.

**LANDLORD:**

[SIGNATURE:Landlord]

Date: _______________

**TENANT:**

[SIGNATURE:Tenant]

Date: _______________

---

*This document was generated using PropManager eDocument System on {{current_date}}.*
"""


def create_lease_template(apps, schema_editor):
    """Create the Residential Lease Agreement template."""
    EDocumentTemplate = apps.get_model("documents", "EDocumentTemplate")

    # Check if template already exists
    if EDocumentTemplate.objects.filter(name="Residential Lease Agreement").exists():
        return

    EDocumentTemplate.objects.create(
        name="Residential Lease Agreement",
        template_type="lease",
        description="Standard residential lease agreement with comprehensive terms covering rent, security deposit, occupancy, utilities, pets, smoking, maintenance, entry rights, and more.",
        content=LEASE_TEMPLATE_CONTENT,
        is_active=True,
    )


def remove_lease_template(apps, schema_editor):
    """Remove the Residential Lease Agreement template."""
    EDocumentTemplate = apps.get_model("documents", "EDocumentTemplate")
    EDocumentTemplate.objects.filter(name="Residential Lease Agreement").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0003_edocument_edocumentsigner_edocumentsignatureblock_and_more"),
    ]

    operations = [
        migrations.RunPython(create_lease_template, remove_lease_template),
    ]
