"""
Additional onboarding presets based on industry best practices.

Adds presets for:
- Corporate Relocation (employer-sponsored moves)
- Military Housing (BAH/military family considerations)
- Roommate / Shared Living (individual roommates)
- Lease Renewal (simplified for existing tenants)
- Month-to-Month Conversion (flexible tenancy conversion)
- Vacation / Short-Term Rental (furnished short stays)

Based on research from:
- Second Nature: 10 Steps to Onboard New Tenants
- Manifestly: Tenant Onboarding Checklist
- Industry best practices for 2025-2026
"""

from django.db import migrations


def create_additional_presets(apps, schema_editor):
    """Create additional system presets for specialized onboarding scenarios."""
    OnboardingPreset = apps.get_model("tenant_lifecycle", "OnboardingPreset")

    presets = [
        # =================================================================
        # Corporate Relocation - Employer-sponsored housing
        # =================================================================
        {
            "name": "Corporate Relocation",
            "description": "Streamlined onboarding for corporate relocations and employer-sponsored "
            "housing. Expedited process with corporate billing options and relocation coordinator support.",
            "category": "residential",
            "icon": "bi-building",
            "is_system": True,
            "steps_config": {
                "account_creation": {"enabled": True, "order": 1, "required": True},
                "personal_info": {"enabled": True, "order": 2, "required": True},
                "emergency_contacts": {"enabled": True, "order": 3, "required": True},
                "occupants": {"enabled": True, "order": 4, "required": True},
                "pets": {"enabled": True, "order": 5, "required": False},
                "vehicles": {"enabled": True, "order": 6, "required": True},
                "employment": {"enabled": True, "order": 7, "required": True},
                "insurance": {"enabled": True, "order": 8, "required": False},
                "id_verification": {"enabled": True, "order": 9, "required": True},
                "documents": {"enabled": True, "order": 10, "required": True},
                "payments": {"enabled": True, "order": 11, "required": True},
                "move_in_schedule": {"enabled": True, "order": 12, "required": True},
                "welcome": {"enabled": True, "order": 13, "required": True},
            },
            "collect_vehicles": True,
            "collect_employment": True,
            "require_renters_insurance": True,
            "require_id_verification": True,
            "link_expiry_days": 10,
            "welcome_message": (
                "Welcome to your corporate housing!\n\n"
                "We understand relocating for work can be stressful. Our team is here to make "
                "your transition as smooth as possible. Your residence is fully prepared "
                "for your arrival.\n\n"
                "If your employer's relocation coordinator needs any documentation, "
                "please have them contact our corporate housing team directly.\n\n"
                "We hope this feels like home."
            ),
            "property_rules": (
                "Corporate Housing Guidelines:\n"
                "• Your lease is coordinated with your employer's relocation program\n"
                "• Quiet hours: 10 PM - 7 AM\n"
                "• Furnished units: Please report any furniture issues immediately\n"
                "• Cleaning service available upon request\n"
                "• Extended stay amenities included\n\n"
                "Services Available:\n"
                "• Concierge package receiving\n"
                "• Local area orientation guide\n"
                "• Airport transportation coordination\n"
                "• Temporary storage available"
            ),
            "move_in_checklist": [
                "Provide employer authorization letter",
                "Submit corporate relocation contact information",
                "Complete employment verification",
                "Set up utilities (or confirm corporate account)",
                "Obtain renter's insurance (or verify corporate policy)",
                "Register vehicles for parking",
                "Schedule move-in with relocation coordinator",
                "Review furnished inventory checklist",
                "Collect all keys and access devices",
                "Download resident portal app",
            ],
            "invitation_email_subject": "Corporate Housing Ready - Complete Your Move-In",
            "invitation_email_body": (
                "Dear {{first_name}},\n\n"
                "Your corporate housing at {{property_name}} is ready for your arrival.\n\n"
                "Please complete your move-in paperwork: {{link}}\n\n"
                "What you'll need:\n"
                "• Government-issued ID\n"
                "• Employer authorization or relocation letter\n"
                "• Employment information\n"
                "• Vehicle registration (if bringing a car)\n\n"
                "Your relocation coordinator has been copied on this communication. "
                "If you have any questions, our corporate housing team is available "
                "to assist.\n\n"
                "Welcome to the area!\n"
                "{{property_name}} Corporate Housing Team"
            ),
            "invitation_sms_body": (
                "Your corporate housing is ready! Complete move-in: {{link}}"
            ),
            "default_fees": [
                {
                    "fee_type": "security_deposit",
                    "name": "Security Deposit",
                    "description": "May be billed to employer per relocation agreement",
                    "use_lease_value": True,
                    "lease_field": "security_deposit",
                    "is_required": True,
                    "is_refundable": True,
                },
                {
                    "fee_type": "first_month",
                    "name": "First Month's Rent",
                    "description": "Billed per corporate agreement",
                    "use_lease_value": True,
                    "lease_field": "monthly_rent",
                    "is_required": True,
                    "is_refundable": False,
                },
            ],
        },
        # =================================================================
        # Military Housing - For service members and families
        # =================================================================
        {
            "name": "Military Housing",
            "description": "Tailored for active duty military, veterans, and military families. "
            "Includes BAH considerations, PCS move support, and military clause acknowledgment.",
            "category": "residential",
            "icon": "bi-flag",
            "is_system": True,
            "steps_config": {
                "account_creation": {"enabled": True, "order": 1, "required": True},
                "personal_info": {"enabled": True, "order": 2, "required": True},
                "emergency_contacts": {"enabled": True, "order": 3, "required": True},
                "occupants": {"enabled": True, "order": 4, "required": True},
                "pets": {"enabled": True, "order": 5, "required": False},
                "vehicles": {"enabled": True, "order": 6, "required": True},
                "employment": {"enabled": True, "order": 7, "required": True},
                "insurance": {"enabled": True, "order": 8, "required": False},
                "id_verification": {"enabled": True, "order": 9, "required": True},
                "documents": {"enabled": True, "order": 10, "required": True},
                "payments": {"enabled": True, "order": 11, "required": True},
                "move_in_schedule": {"enabled": True, "order": 12, "required": True},
                "welcome": {"enabled": True, "order": 13, "required": True},
            },
            "collect_vehicles": True,
            "collect_employment": True,
            "require_renters_insurance": True,
            "require_id_verification": True,
            "link_expiry_days": 21,
            "welcome_message": (
                "Thank you for your service!\n\n"
                "We're honored to welcome you and your family to our community. "
                "We understand military life comes with unique challenges, and we're "
                "committed to supporting you throughout your stay.\n\n"
                "Our lease includes SCRA protections and a military clause for PCS orders. "
                "If you have any questions about your housing benefits or BAH, "
                "our team is here to help."
            ),
            "property_rules": (
                "Military Family Guidelines:\n"
                "• Military clause included - we honor PCS orders\n"
                "• SCRA protections apply\n"
                "• Deployment support available\n"
                "• Family members can handle lease matters with POA\n"
                "• We work with military housing offices\n\n"
                "Community Rules:\n"
                "• Quiet hours: 10 PM - 7 AM\n"
                "• Guest policy accommodates TDY/deployment visitors\n"
                "• Vehicle registration required\n"
                "• Pet policy applies (ESAs welcome with documentation)\n\n"
                "Resources:\n"
                "• Military OneSource: 1-800-342-9647\n"
                "• Local base housing office contact available"
            ),
            "move_in_checklist": [
                "Provide military ID (CAC or dependent ID)",
                "Submit LES (Leave and Earnings Statement)",
                "Provide copy of orders (if applicable)",
                "Notify base housing office of off-base residence",
                "Set up utilities",
                "Obtain renter's insurance",
                "Register vehicles (including on-base decals)",
                "Update DEERS with new address",
                "Schedule move-in walkthrough",
                "Review military clause terms",
            ],
            "invitation_email_subject": "Welcome, Service Member! Complete Your Housing Setup",
            "invitation_email_body": (
                "Dear {{first_name}},\n\n"
                "Thank you for your service. We're pleased to welcome you to {{property_name}}.\n\n"
                "Please complete your move-in paperwork: {{link}}\n\n"
                "What you'll need:\n"
                "• Military ID (CAC or dependent ID)\n"
                "• Recent LES (Leave and Earnings Statement)\n"
                "• Orders (if on PCS)\n"
                "• Vehicle registration\n\n"
                "Our lease includes military clause protections and we honor SCRA. "
                "If you have questions about BAH or need coordination with your "
                "housing office, please let us know.\n\n"
                "Welcome home!\n"
                "{{property_name}} Management"
            ),
            "invitation_sms_body": (
                "Welcome, service member! Complete your housing setup: {{link}}"
            ),
            "default_fees": [
                {
                    "fee_type": "security_deposit",
                    "name": "Security Deposit",
                    "description": "Equal to one month's rent (SCRA limits apply)",
                    "use_lease_value": True,
                    "lease_field": "security_deposit",
                    "is_required": True,
                    "is_refundable": True,
                },
                {
                    "fee_type": "first_month",
                    "name": "First Month's Rent",
                    "description": "Prorated if mid-month move-in",
                    "use_lease_value": True,
                    "lease_field": "monthly_rent",
                    "is_required": True,
                    "is_refundable": False,
                },
                {
                    "fee_type": "admin_fee",
                    "name": "Administrative Fee",
                    "description": "Move-in processing (waived for active duty with orders)",
                    "amount": "0.00",
                    "is_required": False,
                    "is_refundable": False,
                },
            ],
        },
        # =================================================================
        # Roommate / Shared Living - Individual in shared unit
        # =================================================================
        {
            "name": "Roommate / Shared Living",
            "description": "For individual roommates joining a shared living situation. "
            "Focuses on individual verification while linking to existing lease.",
            "category": "residential",
            "icon": "bi-people-fill",
            "is_system": True,
            "steps_config": {
                "account_creation": {"enabled": True, "order": 1, "required": True},
                "personal_info": {"enabled": True, "order": 2, "required": True},
                "emergency_contacts": {"enabled": True, "order": 3, "required": True},
                "occupants": {"enabled": False, "order": 4, "required": False},
                "pets": {"enabled": True, "order": 5, "required": False},
                "vehicles": {"enabled": True, "order": 6, "required": False},
                "employment": {"enabled": True, "order": 7, "required": True},
                "insurance": {"enabled": True, "order": 8, "required": False},
                "id_verification": {"enabled": True, "order": 9, "required": True},
                "documents": {"enabled": True, "order": 10, "required": True},
                "payments": {"enabled": True, "order": 11, "required": True},
                "move_in_schedule": {"enabled": True, "order": 12, "required": True},
                "welcome": {"enabled": True, "order": 13, "required": True},
            },
            "collect_vehicles": True,
            "collect_employment": True,
            "require_renters_insurance": True,
            "require_id_verification": True,
            "link_expiry_days": 14,
            "welcome_message": (
                "Welcome to your new shared home!\n\n"
                "Living with roommates can be a great experience. We've provided some "
                "guidelines to help ensure a positive living situation for everyone.\n\n"
                "Remember: Open communication with your roommates is key to a "
                "harmonious household. Don't hesitate to contact management if "
                "you have any concerns."
            ),
            "property_rules": (
                "Roommate Living Guidelines:\n"
                "• Each roommate is jointly liable under the lease\n"
                "• Rent is due in full - coordinate payments among yourselves\n"
                "• All roommates must be approved by management\n"
                "• Notify management of roommate changes 30+ days in advance\n"
                "• Quiet hours: 10 PM - 8 AM\n\n"
                "Shared Space Etiquette:\n"
                "• Respect common area schedules\n"
                "• Clean up after yourself promptly\n"
                "• Communicate about shared expenses\n"
                "• Agree on guest policies with roommates\n\n"
                "Individual Responsibilities:\n"
                "• Your room is your responsibility\n"
                "• Maintain your own renter's insurance\n"
                "• Report maintenance issues promptly"
            ),
            "move_in_checklist": [
                "Complete individual application/verification",
                "Sign lease addendum adding you as tenant",
                "Meet current roommates (if any)",
                "Agree on rent split with roommates",
                "Set up your portion of utilities (if applicable)",
                "Get renter's insurance with personal liability",
                "Collect your set of keys",
                "Exchange contact info with roommates",
                "Review house rules with roommates",
                "Complete room condition checklist",
            ],
            "invitation_email_subject": "Complete Your Roommate Move-In",
            "invitation_email_body": (
                "Hi {{first_name}},\n\n"
                "Welcome! You're being added to the lease at {{property_name}}.\n\n"
                "Please complete your move-in paperwork: {{link}}\n\n"
                "What you'll need:\n"
                "• Government-issued ID\n"
                "• Proof of income (pay stubs or employment letter)\n"
                "• Renter's insurance information\n\n"
                "You'll be signing a lease addendum that adds you as a tenant. "
                "All roommates share equal responsibility under the lease.\n\n"
                "Questions? Contact our office or your future roommates.\n\n"
                "{{property_name}} Management"
            ),
            "invitation_sms_body": (
                "Complete your roommate move-in paperwork: {{link}}"
            ),
            "default_fees": [
                {
                    "fee_type": "security_deposit",
                    "name": "Security Deposit Contribution",
                    "description": "Your portion of the security deposit",
                    "use_lease_value": False,
                    "amount": "500.00",
                    "is_required": True,
                    "is_refundable": True,
                },
                {
                    "fee_type": "first_month",
                    "name": "First Month's Rent (Your Portion)",
                    "description": "Your share of this month's rent",
                    "use_lease_value": False,
                    "is_required": True,
                    "is_refundable": False,
                },
                {
                    "fee_type": "admin_fee",
                    "name": "Roommate Addition Fee",
                    "description": "Processing fee for adding tenant to lease",
                    "amount": "75.00",
                    "is_required": True,
                    "is_refundable": False,
                },
            ],
        },
        # =================================================================
        # Lease Renewal - Simplified for existing tenants
        # =================================================================
        {
            "name": "Lease Renewal",
            "description": "Streamlined renewal process for existing tenants. "
            "Skips already-verified information and focuses on updated documents and payments.",
            "category": "residential",
            "icon": "bi-arrow-repeat",
            "is_system": True,
            "steps_config": {
                "account_creation": {"enabled": False, "order": 1, "required": False},
                "personal_info": {"enabled": True, "order": 2, "required": True},
                "emergency_contacts": {"enabled": True, "order": 3, "required": True},
                "occupants": {"enabled": True, "order": 4, "required": False},
                "pets": {"enabled": True, "order": 5, "required": False},
                "vehicles": {"enabled": True, "order": 6, "required": False},
                "employment": {"enabled": False, "order": 7, "required": False},
                "insurance": {"enabled": True, "order": 8, "required": False},
                "id_verification": {"enabled": False, "order": 9, "required": False},
                "documents": {"enabled": True, "order": 10, "required": True},
                "payments": {"enabled": False, "order": 11, "required": False},
                "move_in_schedule": {"enabled": False, "order": 12, "required": False},
                "welcome": {"enabled": True, "order": 13, "required": True},
            },
            "collect_vehicles": True,
            "collect_employment": False,
            "require_renters_insurance": False,
            "require_id_verification": False,
            "link_expiry_days": 30,
            "welcome_message": (
                "Thank you for renewing your lease!\n\n"
                "We're delighted you've chosen to continue calling this place home. "
                "Your renewal is now complete.\n\n"
                "Please take a moment to update any contact information that may have "
                "changed. We look forward to another great year together!"
            ),
            "property_rules": "",
            "move_in_checklist": [
                "Review new lease terms and rent amount",
                "Update emergency contacts if needed",
                "Update renter's insurance policy",
                "Report any household changes",
                "Update vehicle information if changed",
                "Sign renewal documents",
            ],
            "invitation_email_subject": "Your Lease Renewal is Ready",
            "invitation_email_body": (
                "Dear {{first_name}},\n\n"
                "Your lease at {{property_name}} is up for renewal. We'd love to have you "
                "continue as our resident!\n\n"
                "Please review and sign your renewal documents: {{link}}\n\n"
                "Your new lease terms:\n"
                "• New term dates\n"
                "• Updated rent amount (if applicable)\n"
                "• Any policy changes\n\n"
                "If you have any questions about the renewal terms, please contact "
                "our office before signing.\n\n"
                "Thank you for being a valued resident!\n"
                "{{property_name}} Management"
            ),
            "invitation_sms_body": (
                "Lease renewal ready! Review and sign: {{link}}"
            ),
            "default_fees": [],
        },
        # =================================================================
        # Month-to-Month Conversion
        # =================================================================
        {
            "name": "Month-to-Month Conversion",
            "description": "For tenants converting from fixed-term to month-to-month tenancy. "
            "Simple acknowledgment of new terms and any rate adjustments.",
            "category": "residential",
            "icon": "bi-calendar-month",
            "is_system": True,
            "steps_config": {
                "account_creation": {"enabled": False, "order": 1, "required": False},
                "personal_info": {"enabled": False, "order": 2, "required": False},
                "emergency_contacts": {"enabled": True, "order": 3, "required": False},
                "occupants": {"enabled": False, "order": 4, "required": False},
                "pets": {"enabled": False, "order": 5, "required": False},
                "vehicles": {"enabled": False, "order": 6, "required": False},
                "employment": {"enabled": False, "order": 7, "required": False},
                "insurance": {"enabled": True, "order": 8, "required": False},
                "id_verification": {"enabled": False, "order": 9, "required": False},
                "documents": {"enabled": True, "order": 10, "required": True},
                "payments": {"enabled": False, "order": 11, "required": False},
                "move_in_schedule": {"enabled": False, "order": 12, "required": False},
                "welcome": {"enabled": True, "order": 13, "required": True},
            },
            "collect_vehicles": False,
            "collect_employment": False,
            "require_renters_insurance": False,
            "require_id_verification": False,
            "link_expiry_days": 14,
            "welcome_message": (
                "Your tenancy has been converted to month-to-month.\n\n"
                "This provides you with flexibility while maintaining your residency. "
                "Please note that either party may terminate with 30 days' written notice.\n\n"
                "Your rent amount may have been adjusted for the month-to-month term. "
                "Review your new agreement for details."
            ),
            "property_rules": (
                "Month-to-Month Terms:\n"
                "• 30 days' written notice required to terminate\n"
                "• Rent may be adjusted with 30 days' notice\n"
                "• All other lease terms remain in effect\n"
                "• You can convert back to a fixed term anytime"
            ),
            "move_in_checklist": [
                "Review month-to-month terms",
                "Note any rent adjustments",
                "Update renter's insurance if needed",
                "Sign month-to-month agreement",
            ],
            "invitation_email_subject": "Your Month-to-Month Agreement",
            "invitation_email_body": (
                "Dear {{first_name}},\n\n"
                "Your lease has been converted to a month-to-month tenancy.\n\n"
                "Please review and sign your new agreement: {{link}}\n\n"
                "Key changes:\n"
                "• Flexible tenancy (30 days' notice to terminate)\n"
                "• Any rent adjustments for the new term\n\n"
                "If you'd prefer to lock in a new fixed-term lease instead, "
                "please contact our office.\n\n"
                "{{property_name}} Management"
            ),
            "invitation_sms_body": (
                "Month-to-month agreement ready: {{link}}"
            ),
            "default_fees": [],
        },
        # =================================================================
        # Vacation / Short-Term Rental
        # =================================================================
        {
            "name": "Vacation / Short-Term Rental",
            "description": "For furnished short-term rentals, vacation properties, and corporate "
            "stays under 6 months. Includes inventory checklist and house rules acknowledgment.",
            "category": "residential",
            "icon": "bi-umbrella-beach",
            "is_system": True,
            "steps_config": {
                "account_creation": {"enabled": True, "order": 1, "required": True},
                "personal_info": {"enabled": True, "order": 2, "required": True},
                "emergency_contacts": {"enabled": True, "order": 3, "required": True},
                "occupants": {"enabled": True, "order": 4, "required": True},
                "pets": {"enabled": True, "order": 5, "required": False},
                "vehicles": {"enabled": True, "order": 6, "required": True},
                "employment": {"enabled": False, "order": 7, "required": False},
                "insurance": {"enabled": False, "order": 8, "required": False},
                "id_verification": {"enabled": True, "order": 9, "required": True},
                "documents": {"enabled": True, "order": 10, "required": True},
                "payments": {"enabled": True, "order": 11, "required": True},
                "move_in_schedule": {"enabled": True, "order": 12, "required": True},
                "welcome": {"enabled": True, "order": 13, "required": True},
            },
            "collect_vehicles": True,
            "collect_employment": False,
            "require_renters_insurance": False,
            "require_id_verification": True,
            "link_expiry_days": 7,
            "welcome_message": (
                "Welcome to your home away from home!\n\n"
                "Your furnished rental is ready and waiting for you. We've prepared "
                "everything for your arrival including fresh linens and a welcome kit.\n\n"
                "Inside you'll find:\n"
                "• WiFi password and smart TV instructions\n"
                "• Local area guide with restaurants and attractions\n"
                "• Emergency contact information\n"
                "• Checkout procedures\n\n"
                "Enjoy your stay!"
            ),
            "property_rules": (
                "Short-Term Rental Guidelines:\n"
                "• Check-in: 3:00 PM / Check-out: 11:00 AM\n"
                "• Maximum occupancy as stated in your agreement\n"
                "• No parties or events without prior approval\n"
                "• Quiet hours: 10 PM - 8 AM\n"
                "• No smoking (including balconies)\n"
                "• Pets only with prior approval and fee\n\n"
                "Included Amenities:\n"
                "• Fully furnished with linens and towels\n"
                "• Full kitchen with cookware\n"
                "• Washer/dryer (or nearby laundry)\n"
                "• High-speed WiFi\n"
                "• Streaming TV services\n"
                "• Parking as assigned\n\n"
                "Checkout:\n"
                "• Start dishwasher\n"
                "• Remove all trash\n"
                "• Strip beds (leave linens on beds)\n"
                "• Return keys to lockbox"
            ),
            "move_in_checklist": [
                "Review rental agreement and house rules",
                "Complete guest registration",
                "Pay rental amount and security deposit",
                "Receive access codes / key information",
                "Review furnished inventory",
                "Note check-in and check-out times",
                "Save emergency contact numbers",
                "Review parking instructions",
            ],
            "invitation_email_subject": "Your Vacation Rental is Confirmed!",
            "invitation_email_body": (
                "Hi {{first_name}},\n\n"
                "Your vacation rental at {{property_name}} is confirmed!\n\n"
                "Please complete your guest registration: {{link}}\n\n"
                "Rental Details:\n"
                "• Check-in: 3:00 PM\n"
                "• Check-out: 11:00 AM\n"
                "• Maximum guests: As listed in your booking\n\n"
                "After completing registration, you'll receive:\n"
                "• Access codes and entry instructions\n"
                "• WiFi password\n"
                "• Local area guide\n\n"
                "We hope you have a wonderful stay!\n"
                "{{property_name}}"
            ),
            "invitation_sms_body": (
                "Vacation rental confirmed! Complete registration: {{link}}"
            ),
            "default_fees": [
                {
                    "fee_type": "security_deposit",
                    "name": "Security/Damage Deposit",
                    "description": "Refundable deposit, returned after checkout inspection",
                    "amount": "500.00",
                    "is_required": True,
                    "is_refundable": True,
                },
                {
                    "fee_type": "first_month",
                    "name": "Rental Amount",
                    "description": "Full rental amount for stay",
                    "use_lease_value": True,
                    "lease_field": "monthly_rent",
                    "is_required": True,
                    "is_refundable": False,
                },
                {
                    "fee_type": "cleaning_fee",
                    "name": "Cleaning Fee",
                    "description": "Professional cleaning after checkout",
                    "amount": "150.00",
                    "is_required": True,
                    "is_refundable": False,
                },
                {
                    "fee_type": "pet_fee",
                    "name": "Pet Fee",
                    "description": "Per pet, if applicable",
                    "amount": "75.00",
                    "is_required": False,
                    "is_refundable": False,
                },
            ],
        },
        # =================================================================
        # Low Income Housing Tax Credit (LIHTC)
        # =================================================================
        {
            "name": "Affordable Housing (LIHTC)",
            "description": "For Low Income Housing Tax Credit properties. Includes required "
            "income certification, household composition verification, and compliance documentation.",
            "category": "subsidized",
            "icon": "bi-house-heart",
            "is_system": True,
            "steps_config": {
                "account_creation": {"enabled": True, "order": 1, "required": True},
                "personal_info": {"enabled": True, "order": 2, "required": True},
                "emergency_contacts": {"enabled": True, "order": 3, "required": True},
                "occupants": {"enabled": True, "order": 4, "required": True},
                "pets": {"enabled": True, "order": 5, "required": False},
                "vehicles": {"enabled": True, "order": 6, "required": False},
                "employment": {"enabled": True, "order": 7, "required": True},
                "insurance": {"enabled": True, "order": 8, "required": False},
                "id_verification": {"enabled": True, "order": 9, "required": True},
                "documents": {"enabled": True, "order": 10, "required": True},
                "payments": {"enabled": True, "order": 11, "required": True},
                "move_in_schedule": {"enabled": True, "order": 12, "required": True},
                "welcome": {"enabled": True, "order": 13, "required": True},
            },
            "collect_vehicles": True,
            "collect_employment": True,
            "require_renters_insurance": False,
            "require_id_verification": True,
            "link_expiry_days": 30,
            "welcome_message": (
                "Welcome to your new home!\n\n"
                "This property participates in the Low Income Housing Tax Credit (LIHTC) "
                "program, which helps provide quality affordable housing.\n\n"
                "As a resident, you'll need to complete annual income recertification "
                "to maintain eligibility. Please report any income or household changes "
                "promptly to ensure continued compliance.\n\n"
                "We're here to help - contact our office with any questions."
            ),
            "property_rules": (
                "LIHTC Compliance Requirements:\n"
                "• Annual income recertification required\n"
                "• Report all income changes within 30 days\n"
                "• Report all household composition changes\n"
                "• All occupants must be listed and approved\n"
                "• Student status restrictions may apply\n\n"
                "Documentation to Keep Current:\n"
                "• Employment verification\n"
                "• Government benefit statements\n"
                "• Tax returns (if self-employed)\n"
                "• Child support/alimony documentation\n\n"
                "Community Rules:\n"
                "• Quiet hours: 10 PM - 8 AM\n"
                "• Keep unit in good condition\n"
                "• Report maintenance promptly\n"
                "• Allow access for required inspections"
            ),
            "move_in_checklist": [
                "Complete Tenant Income Certification (TIC)",
                "Provide income documentation for all household members",
                "Provide ID and Social Security cards for all occupants",
                "Complete student status certification (if applicable)",
                "Sign LIHTC lease addendum",
                "Set up utilities",
                "Complete move-in inspection",
                "Review recertification schedule",
            ],
            "invitation_email_subject": "Complete Your Affordable Housing Application",
            "invitation_email_body": (
                "Dear {{first_name}},\n\n"
                "Please complete your move-in paperwork for {{property_name}}: {{link}}\n\n"
                "Required documentation:\n"
                "• Income verification for ALL household members\n"
                "  - Pay stubs (4 most recent)\n"
                "  - Benefit statements (SSI, TANF, etc.)\n"
                "  - Tax returns (if self-employed)\n"
                "• Government-issued ID for all adults\n"
                "• Social Security cards for all occupants\n"
                "• Birth certificates for minors\n"
                "• Student status verification (if any household member is a student)\n\n"
                "Complete documentation is required to verify program eligibility.\n\n"
                "{{property_name}} Management"
            ),
            "invitation_sms_body": (
                "Complete your affordable housing paperwork: {{link}} - Bring income docs for all household members."
            ),
            "default_fees": [
                {
                    "fee_type": "security_deposit",
                    "name": "Security Deposit",
                    "description": "Payment plans may be available - ask management",
                    "use_lease_value": True,
                    "lease_field": "security_deposit",
                    "is_required": True,
                    "is_refundable": True,
                },
                {
                    "fee_type": "first_month",
                    "name": "First Month's Rent",
                    "description": "Prorated if applicable",
                    "use_lease_value": True,
                    "lease_field": "monthly_rent",
                    "is_required": True,
                    "is_refundable": False,
                },
            ],
        },
    ]

    for preset_data in presets:
        # Only create if doesn't exist
        if not OnboardingPreset.objects.filter(name=preset_data["name"]).exists():
            OnboardingPreset.objects.create(**preset_data)


def remove_additional_presets(apps, schema_editor):
    """Remove additional system presets."""
    OnboardingPreset = apps.get_model("tenant_lifecycle", "OnboardingPreset")

    preset_names = [
        "Corporate Relocation",
        "Military Housing",
        "Roommate / Shared Living",
        "Lease Renewal",
        "Month-to-Month Conversion",
        "Vacation / Short-Term Rental",
        "Affordable Housing (LIHTC)",
    ]

    OnboardingPreset.objects.filter(name__in=preset_names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("tenant_lifecycle", "0004_seed_onboarding_presets"),
    ]

    operations = [
        migrations.RunPython(create_additional_presets, remove_additional_presets),
    ]
