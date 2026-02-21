"""
Seed onboarding presets with common template configurations.
"""

from django.db import migrations


def create_presets(apps, schema_editor):
    """Create system presets for common onboarding scenarios."""
    OnboardingPreset = apps.get_model("tenant_lifecycle", "OnboardingPreset")

    presets = [
        # =================================================================
        # Standard Residential - Full onboarding with all standard steps
        # =================================================================
        {
            "name": "Standard Residential",
            "description": "Complete onboarding for standard residential properties. "
            "Includes all common steps: emergency contacts, occupants, pets, vehicles, "
            "employment verification, documents, and payments.",
            "category": "residential",
            "icon": "bi-house-door",
            "is_system": True,
            "steps_config": {
                "account_creation": {"enabled": True, "order": 1, "required": True},
                "personal_info": {"enabled": True, "order": 2, "required": True},
                "emergency_contacts": {"enabled": True, "order": 3, "required": True},
                "occupants": {"enabled": True, "order": 4, "required": False},
                "pets": {"enabled": True, "order": 5, "required": False},
                "vehicles": {"enabled": True, "order": 6, "required": False},
                "employment": {"enabled": True, "order": 7, "required": False},
                "insurance": {"enabled": True, "order": 8, "required": False},
                "id_verification": {"enabled": False, "order": 9, "required": False},
                "documents": {"enabled": True, "order": 10, "required": True},
                "payments": {"enabled": True, "order": 11, "required": True},
                "move_in_schedule": {"enabled": True, "order": 12, "required": False},
                "welcome": {"enabled": True, "order": 13, "required": True},
            },
            "collect_vehicles": True,
            "collect_employment": True,
            "require_renters_insurance": False,
            "require_id_verification": False,
            "link_expiry_days": 14,
            "welcome_message": (
                "Welcome to your new home! We're excited to have you as a resident.\n\n"
                "Please review the property information below and don't hesitate to "
                "contact the management office if you have any questions."
            ),
            "property_rules": (
                "• Quiet hours are from 10 PM to 8 AM\n"
                "• No smoking in units or common areas\n"
                "• Dispose of trash in designated areas only\n"
                "• Report maintenance issues promptly\n"
                "• Notify management of extended absences\n"
                "• Respect your neighbors and shared spaces"
            ),
            "move_in_checklist": [
                "Set up utilities in your name",
                "Get renter's insurance",
                "Change your mailing address",
                "Schedule a move-in walkthrough",
                "Collect all keys and access devices",
                "Review emergency procedures",
                "Locate fire extinguisher and exits",
                "Test smoke detectors",
            ],
            "invitation_email_subject": "Welcome! Complete Your Move-In Process",
            "invitation_email_body": (
                "Hi {{first_name}},\n\n"
                "We're excited to welcome you to {{property_name}}! "
                "Please complete your move-in paperwork by clicking the link below.\n\n"
                "{{link}}\n\n"
                "This link will expire in {{expiry_days}} days. "
                "If you have any questions, please contact our office.\n\n"
                "Best regards,\n"
                "{{property_name}} Management"
            ),
            "invitation_sms_body": (
                "Welcome to {{property_name}}! Complete your move-in at: {{link}}"
            ),
            "default_fees": [
                {
                    "fee_type": "security_deposit",
                    "name": "Security Deposit",
                    "description": "Refundable security deposit",
                    "use_lease_value": True,
                    "lease_field": "security_deposit",
                    "is_required": True,
                    "is_refundable": True,
                },
                {
                    "fee_type": "first_month",
                    "name": "First Month's Rent",
                    "description": "First month's rent due at move-in",
                    "use_lease_value": True,
                    "lease_field": "monthly_rent",
                    "is_required": True,
                    "is_refundable": False,
                },
            ],
        },
        # =================================================================
        # Quick Move-In - Minimal steps for fast processing
        # =================================================================
        {
            "name": "Quick Move-In",
            "description": "Streamlined onboarding with only essential steps. "
            "Ideal for returning tenants, corporate relocations, or when speed is priority.",
            "category": "residential",
            "icon": "bi-lightning",
            "is_system": True,
            "steps_config": {
                "account_creation": {"enabled": True, "order": 1, "required": True},
                "personal_info": {"enabled": True, "order": 2, "required": True},
                "emergency_contacts": {"enabled": True, "order": 3, "required": True},
                "occupants": {"enabled": False, "order": 4, "required": False},
                "pets": {"enabled": False, "order": 5, "required": False},
                "vehicles": {"enabled": False, "order": 6, "required": False},
                "employment": {"enabled": False, "order": 7, "required": False},
                "insurance": {"enabled": False, "order": 8, "required": False},
                "id_verification": {"enabled": False, "order": 9, "required": False},
                "documents": {"enabled": True, "order": 10, "required": True},
                "payments": {"enabled": True, "order": 11, "required": True},
                "move_in_schedule": {"enabled": False, "order": 12, "required": False},
                "welcome": {"enabled": True, "order": 13, "required": True},
            },
            "collect_vehicles": False,
            "collect_employment": False,
            "require_renters_insurance": False,
            "require_id_verification": False,
            "link_expiry_days": 7,
            "welcome_message": (
                "Welcome! Your account is set up and you're ready to move in.\n\n"
                "Contact the management office for your keys and access information."
            ),
            "property_rules": "",
            "move_in_checklist": [
                "Pick up keys from office",
                "Complete move-in walkthrough",
            ],
            "invitation_email_subject": "Quick Move-In - Complete in Minutes",
            "invitation_email_body": (
                "Hi {{first_name}},\n\n"
                "Complete your quick move-in paperwork: {{link}}\n\n"
                "This streamlined process takes just a few minutes.\n\n"
                "{{property_name}} Management"
            ),
            "invitation_sms_body": "Complete your quick move-in: {{link}}",
            "default_fees": [
                {
                    "fee_type": "security_deposit",
                    "name": "Security Deposit",
                    "use_lease_value": True,
                    "lease_field": "security_deposit",
                    "is_required": True,
                    "is_refundable": True,
                },
                {
                    "fee_type": "first_month",
                    "name": "First Month's Rent",
                    "use_lease_value": True,
                    "lease_field": "monthly_rent",
                    "is_required": True,
                    "is_refundable": False,
                },
            ],
        },
        # =================================================================
        # Pet-Friendly - Standard + required pet information
        # =================================================================
        {
            "name": "Pet-Friendly Property",
            "description": "Standard onboarding with required pet registration. "
            "Includes pet deposit and mandatory pet documentation.",
            "category": "residential",
            "icon": "bi-heart",
            "is_system": True,
            "steps_config": {
                "account_creation": {"enabled": True, "order": 1, "required": True},
                "personal_info": {"enabled": True, "order": 2, "required": True},
                "emergency_contacts": {"enabled": True, "order": 3, "required": True},
                "occupants": {"enabled": True, "order": 4, "required": False},
                "pets": {"enabled": True, "order": 5, "required": True},
                "vehicles": {"enabled": True, "order": 6, "required": False},
                "employment": {"enabled": True, "order": 7, "required": False},
                "insurance": {"enabled": True, "order": 8, "required": False},
                "id_verification": {"enabled": False, "order": 9, "required": False},
                "documents": {"enabled": True, "order": 10, "required": True},
                "payments": {"enabled": True, "order": 11, "required": True},
                "move_in_schedule": {"enabled": True, "order": 12, "required": False},
                "welcome": {"enabled": True, "order": 13, "required": True},
            },
            "collect_vehicles": True,
            "collect_employment": True,
            "require_renters_insurance": False,
            "require_id_verification": False,
            "link_expiry_days": 14,
            "welcome_message": (
                "Welcome to your new pet-friendly home!\n\n"
                "We're happy to welcome both you and your furry family members. "
                "Please review our pet policies and designated pet areas."
            ),
            "property_rules": (
                "Pet Guidelines:\n"
                "• All pets must be registered with management\n"
                "• Dogs must be leashed in common areas\n"
                "• Clean up after your pets immediately\n"
                "• Use designated pet relief areas\n"
                "• Keep vaccinations current\n"
                "• Excessive noise/barking must be controlled\n"
                "• Breed restrictions may apply - check with management\n\n"
                "General Rules:\n"
                "• Quiet hours: 10 PM - 8 AM\n"
                "• No smoking in units or common areas"
            ),
            "move_in_checklist": [
                "Register all pets with management",
                "Provide vaccination records",
                "Set up utilities",
                "Get renter's insurance with pet liability",
                "Review pet relief area locations",
                "Schedule move-in walkthrough",
            ],
            "invitation_email_subject": "Welcome to Your Pet-Friendly Home!",
            "invitation_email_body": (
                "Hi {{first_name}},\n\n"
                "We're excited to welcome you (and your pets!) to {{property_name}}.\n\n"
                "Please complete your move-in paperwork, including pet registration: {{link}}\n\n"
                "Make sure to have your pet's vaccination records handy.\n\n"
                "{{property_name}} Management"
            ),
            "invitation_sms_body": (
                "Welcome to {{property_name}}! Complete move-in & pet registration: {{link}}"
            ),
            "default_fees": [
                {
                    "fee_type": "security_deposit",
                    "name": "Security Deposit",
                    "use_lease_value": True,
                    "lease_field": "security_deposit",
                    "is_required": True,
                    "is_refundable": True,
                },
                {
                    "fee_type": "first_month",
                    "name": "First Month's Rent",
                    "use_lease_value": True,
                    "lease_field": "monthly_rent",
                    "is_required": True,
                    "is_refundable": False,
                },
                {
                    "fee_type": "pet_deposit",
                    "name": "Pet Deposit",
                    "description": "Refundable pet deposit per pet",
                    "amount": "300.00",
                    "is_required": True,
                    "is_refundable": True,
                },
                {
                    "fee_type": "pet_fee",
                    "name": "Pet Fee",
                    "description": "Non-refundable pet processing fee",
                    "amount": "150.00",
                    "is_required": True,
                    "is_refundable": False,
                },
            ],
        },
        # =================================================================
        # Student Housing
        # =================================================================
        {
            "name": "Student Housing",
            "description": "Tailored for student tenants. Requires guarantor/co-signer "
            "information, ID verification, and academic year timing.",
            "category": "student",
            "icon": "bi-mortarboard",
            "is_system": True,
            "steps_config": {
                "account_creation": {"enabled": True, "order": 1, "required": True},
                "personal_info": {"enabled": True, "order": 2, "required": True},
                "emergency_contacts": {"enabled": True, "order": 3, "required": True},
                "occupants": {"enabled": True, "order": 4, "required": False},
                "pets": {"enabled": False, "order": 5, "required": False},
                "vehicles": {"enabled": True, "order": 6, "required": False},
                "employment": {"enabled": True, "order": 7, "required": False},
                "insurance": {"enabled": True, "order": 8, "required": False},
                "id_verification": {"enabled": True, "order": 9, "required": True},
                "documents": {"enabled": True, "order": 10, "required": True},
                "payments": {"enabled": True, "order": 11, "required": True},
                "move_in_schedule": {"enabled": True, "order": 12, "required": True},
                "welcome": {"enabled": True, "order": 13, "required": True},
            },
            "collect_vehicles": True,
            "collect_employment": False,
            "require_renters_insurance": True,
            "require_id_verification": True,
            "link_expiry_days": 21,
            "welcome_message": (
                "Welcome, student! We're excited to have you join our community.\n\n"
                "Our property is designed with students in mind - we have study areas, "
                "high-speed internet, and proximity to campus.\n\n"
                "Focus on your studies - we'll take care of the rest!"
            ),
            "property_rules": (
                "Community Guidelines:\n"
                "• Quiet hours: 10 PM - 8 AM (extended during finals)\n"
                "• Study areas open 24/7\n"
                "• Guest policy: Max 2 overnight guests, 3 consecutive nights\n"
                "• No parties without prior approval\n"
                "• Parking permits required for all vehicles\n"
                "• Recycling is mandatory\n\n"
                "Academic Success:\n"
                "• Free WiFi throughout the property\n"
                "• Study rooms available for reservation\n"
                "• We offer storage during breaks"
            ),
            "move_in_checklist": [
                "Bring valid student ID",
                "Ensure guarantor has signed documents",
                "Set up utilities (or confirm included)",
                "Get renter's insurance",
                "Register your vehicle for parking",
                "Pick up access card/fob",
                "Connect to resident WiFi",
                "Download community app",
            ],
            "invitation_email_subject": "🎓 Welcome Student! Complete Your Housing Setup",
            "invitation_email_body": (
                "Hi {{first_name}},\n\n"
                "Welcome to {{property_name}}! We're excited to have you as part of "
                "our student community.\n\n"
                "Please complete your move-in paperwork: {{link}}\n\n"
                "You'll need:\n"
                "• Valid student ID\n"
                "• Guarantor/Parent information (if applicable)\n"
                "• Renter's insurance details\n\n"
                "Questions? Our student housing team is here to help!\n\n"
                "{{property_name}} Management"
            ),
            "invitation_sms_body": (
                "Welcome student! Complete your housing setup at {{property_name}}: {{link}}"
            ),
            "default_fees": [
                {
                    "fee_type": "security_deposit",
                    "name": "Security Deposit",
                    "use_lease_value": True,
                    "lease_field": "security_deposit",
                    "is_required": True,
                    "is_refundable": True,
                },
                {
                    "fee_type": "first_month",
                    "name": "First Month's Rent",
                    "use_lease_value": True,
                    "lease_field": "monthly_rent",
                    "is_required": True,
                    "is_refundable": False,
                },
                {
                    "fee_type": "admin_fee",
                    "name": "Student Housing Fee",
                    "description": "One-time administrative fee",
                    "amount": "100.00",
                    "is_required": True,
                    "is_refundable": False,
                },
            ],
        },
        # =================================================================
        # Senior Living
        # =================================================================
        {
            "name": "Senior Living",
            "description": "Designed for 55+ communities. Simplified steps with "
            "focus on emergency contacts and accessibility information.",
            "category": "senior",
            "icon": "bi-people",
            "is_system": True,
            "steps_config": {
                "account_creation": {"enabled": True, "order": 1, "required": True},
                "personal_info": {"enabled": True, "order": 2, "required": True},
                "emergency_contacts": {"enabled": True, "order": 3, "required": True},
                "occupants": {"enabled": True, "order": 4, "required": True},
                "pets": {"enabled": True, "order": 5, "required": False},
                "vehicles": {"enabled": True, "order": 6, "required": False},
                "employment": {"enabled": False, "order": 7, "required": False},
                "insurance": {"enabled": True, "order": 8, "required": False},
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
            "link_expiry_days": 21,
            "welcome_message": (
                "Welcome to our community!\n\n"
                "We're delighted to have you join us. Our community is designed "
                "for active adults who value comfort, security, and connection.\n\n"
                "Please don't hesitate to reach out if you need any assistance "
                "during your move-in process."
            ),
            "property_rules": (
                "Community Guidelines:\n"
                "• Age verification required (55+ community)\n"
                "• Quiet hours: 9 PM - 8 AM\n"
                "• Guests welcome (notify office for extended stays)\n"
                "• Community center open daily 8 AM - 8 PM\n"
                "• Emergency pull cords in each unit - test monthly\n"
                "• Mobility devices may be used in common areas\n\n"
                "Safety:\n"
                "• 24/7 emergency maintenance\n"
                "• Security patrol nightly\n"
                "• Well-lit walkways and parking"
            ),
            "move_in_checklist": [
                "Provide age verification documentation",
                "Complete emergency contact forms",
                "Register any medical equipment needs",
                "Schedule move-in walkthrough",
                "Collect all keys and access devices",
                "Review emergency procedures",
                "Register for community activities",
                "Set up mail forwarding",
            ],
            "invitation_email_subject": "Welcome to Our Senior Community",
            "invitation_email_body": (
                "Dear {{first_name}},\n\n"
                "We're pleased to welcome you to {{property_name}}.\n\n"
                "Please complete your move-in paperwork at your convenience: {{link}}\n\n"
                "If you need any assistance or prefer to complete this process "
                "in person, please contact our office and we'll be happy to help.\n\n"
                "Warm regards,\n"
                "{{property_name}} Management"
            ),
            "invitation_sms_body": (
                "Welcome to {{property_name}}! Complete your move-in: {{link}} "
                "Call us if you need help."
            ),
            "default_fees": [
                {
                    "fee_type": "security_deposit",
                    "name": "Security Deposit",
                    "use_lease_value": True,
                    "lease_field": "security_deposit",
                    "is_required": True,
                    "is_refundable": True,
                },
                {
                    "fee_type": "first_month",
                    "name": "First Month's Rent",
                    "use_lease_value": True,
                    "lease_field": "monthly_rent",
                    "is_required": True,
                    "is_refundable": False,
                },
            ],
        },
        # =================================================================
        # Section 8 / Subsidized Housing
        # =================================================================
        {
            "name": "Subsidized Housing (Section 8)",
            "description": "For Section 8 voucher holders and subsidized housing programs. "
            "Includes required income verification and documentation.",
            "category": "subsidized",
            "icon": "bi-shield-check",
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
                "We're committed to providing quality affordable housing. "
                "Please review your lease carefully and don't hesitate to contact "
                "us if you have questions about your voucher or rent portion.\n\n"
                "Remember to report any income changes promptly."
            ),
            "property_rules": (
                "Important Reminders:\n"
                "• Report all income changes within 30 days\n"
                "• Annual recertification is required\n"
                "• All occupants must be approved and listed on lease\n"
                "• Maintain unit in good condition\n"
                "• Allow access for required inspections\n\n"
                "Community Rules:\n"
                "• Quiet hours: 10 PM - 8 AM\n"
                "• No unauthorized alterations to unit\n"
                "• Keep common areas clean\n"
                "• Report maintenance issues promptly"
            ),
            "move_in_checklist": [
                "Provide voucher documentation",
                "Submit income verification",
                "Provide ID for all household members",
                "Complete Housing Authority paperwork",
                "Set up utilities (tenant portion)",
                "Schedule HQS inspection",
                "Complete move-in walkthrough",
                "Review rent payment procedures",
            ],
            "invitation_email_subject": "Complete Your Housing Paperwork",
            "invitation_email_body": (
                "Dear {{first_name}},\n\n"
                "Please complete your move-in paperwork for {{property_name}}: {{link}}\n\n"
                "You will need:\n"
                "• Housing voucher information\n"
                "• Income verification documents\n"
                "• ID for all household members\n"
                "• Social Security cards\n\n"
                "The link expires in {{expiry_days}} days. Contact us if you need "
                "more time or assistance.\n\n"
                "{{property_name}} Management"
            ),
            "invitation_sms_body": (
                "Complete your housing paperwork: {{link}} - Bring income docs & IDs."
            ),
            "default_fees": [
                {
                    "fee_type": "security_deposit",
                    "name": "Security Deposit",
                    "description": "May be paid in installments - ask management",
                    "use_lease_value": True,
                    "lease_field": "security_deposit",
                    "is_required": True,
                    "is_refundable": True,
                },
                {
                    "fee_type": "first_month",
                    "name": "Tenant Portion - First Month",
                    "description": "Your portion of first month's rent",
                    "use_lease_value": False,
                    "is_required": True,
                    "is_refundable": False,
                },
            ],
        },
        # =================================================================
        # Luxury / High-End
        # =================================================================
        {
            "name": "Luxury Residential",
            "description": "Premium onboarding experience for luxury properties. "
            "Comprehensive verification with concierge-level service.",
            "category": "residential",
            "icon": "bi-gem",
            "is_system": True,
            "steps_config": {
                "account_creation": {"enabled": True, "order": 1, "required": True},
                "personal_info": {"enabled": True, "order": 2, "required": True},
                "emergency_contacts": {"enabled": True, "order": 3, "required": True},
                "occupants": {"enabled": True, "order": 4, "required": True},
                "pets": {"enabled": True, "order": 5, "required": False},
                "vehicles": {"enabled": True, "order": 6, "required": True},
                "employment": {"enabled": True, "order": 7, "required": True},
                "insurance": {"enabled": True, "order": 8, "required": True},
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
                "Welcome to luxury living.\n\n"
                "Your residence is more than just an apartment - it's an experience. "
                "Our concierge team is available to assist you with anything you need.\n\n"
                "Enjoy our premium amenities including the rooftop lounge, fitness center, "
                "and private parking garage. We look forward to exceeding your expectations."
            ),
            "property_rules": (
                "Residence Guidelines:\n"
                "• 24/7 concierge service available\n"
                "• Package receiving and cold storage available\n"
                "• Valet parking available for guests\n"
                "• Private events require advance booking\n"
                "• Noise considerations apply at all times\n\n"
                "Amenities:\n"
                "• Rooftop lounge: 6 AM - 12 AM\n"
                "• Fitness center: 24/7 with key card\n"
                "• Pool: 6 AM - 10 PM\n"
                "• Business center: 24/7\n"
                "• Wine storage: Available for rent"
            ),
            "move_in_checklist": [
                "Schedule white-glove move-in service",
                "Set up concierge preferences",
                "Register vehicles for garage",
                "Configure smart home system",
                "Review amenity reservations",
                "Schedule walkthrough with property manager",
                "Set up package delivery preferences",
                "Order parking passes for guests",
            ],
            "invitation_email_subject": "Welcome to Your New Residence",
            "invitation_email_body": (
                "Dear {{first_name}},\n\n"
                "We are pleased to welcome you to {{property_name}}.\n\n"
                "Please complete your residence onboarding at: {{link}}\n\n"
                "Our concierge team will follow up to schedule your personalized "
                "move-in experience. If you require any special arrangements, "
                "please don't hesitate to let us know.\n\n"
                "We look forward to providing you with an exceptional living experience.\n\n"
                "Warm regards,\n"
                "{{property_name}} Management"
            ),
            "invitation_sms_body": (
                "Welcome to {{property_name}}. Complete your residence onboarding: {{link}}"
            ),
            "default_fees": [
                {
                    "fee_type": "security_deposit",
                    "name": "Security Deposit",
                    "use_lease_value": True,
                    "lease_field": "security_deposit",
                    "is_required": True,
                    "is_refundable": True,
                },
                {
                    "fee_type": "first_month",
                    "name": "First Month's Rent",
                    "use_lease_value": True,
                    "lease_field": "monthly_rent",
                    "is_required": True,
                    "is_refundable": False,
                },
                {
                    "fee_type": "last_month",
                    "name": "Last Month's Rent",
                    "use_lease_value": True,
                    "lease_field": "monthly_rent",
                    "is_required": True,
                    "is_refundable": False,
                },
                {
                    "fee_type": "key_deposit",
                    "name": "Key Fob / Access Card Deposit",
                    "amount": "100.00",
                    "is_required": True,
                    "is_refundable": True,
                },
                {
                    "fee_type": "parking_fee",
                    "name": "Reserved Parking Space",
                    "description": "First month parking fee",
                    "amount": "200.00",
                    "is_required": False,
                    "is_refundable": False,
                },
            ],
        },
        # =================================================================
        # Commercial / Office Space
        # =================================================================
        {
            "name": "Commercial Tenant",
            "description": "For commercial and office space tenants. "
            "Business-focused onboarding with liability requirements.",
            "category": "commercial",
            "icon": "bi-briefcase",
            "is_system": True,
            "steps_config": {
                "account_creation": {"enabled": True, "order": 1, "required": True},
                "personal_info": {"enabled": True, "order": 2, "required": True},
                "emergency_contacts": {"enabled": True, "order": 3, "required": True},
                "occupants": {"enabled": False, "order": 4, "required": False},
                "pets": {"enabled": False, "order": 5, "required": False},
                "vehicles": {"enabled": True, "order": 6, "required": False},
                "employment": {"enabled": False, "order": 7, "required": False},
                "insurance": {"enabled": True, "order": 8, "required": True},
                "id_verification": {"enabled": True, "order": 9, "required": True},
                "documents": {"enabled": True, "order": 10, "required": True},
                "payments": {"enabled": True, "order": 11, "required": True},
                "move_in_schedule": {"enabled": True, "order": 12, "required": True},
                "welcome": {"enabled": True, "order": 13, "required": True},
            },
            "collect_vehicles": True,
            "collect_employment": False,
            "require_renters_insurance": True,
            "require_id_verification": True,
            "link_expiry_days": 30,
            "welcome_message": (
                "Welcome to {{property_name}}!\n\n"
                "We're pleased to have your business join our commercial community. "
                "Our team is here to support your success.\n\n"
                "Please review building access procedures, loading dock schedules, "
                "and emergency protocols. Contact building management for any "
                "special requirements."
            ),
            "property_rules": (
                "Building Operations:\n"
                "• Business hours: 7 AM - 7 PM (24/7 access with key card)\n"
                "• Loading dock: Schedule 24 hours in advance\n"
                "• HVAC requests: Submit via tenant portal\n"
                "• After-hours access logged for security\n"
                "• Maintenance requests via online portal\n\n"
                "Requirements:\n"
                "• Maintain current liability insurance\n"
                "• Provide updated emergency contacts annually\n"
                "• Comply with building signage guidelines\n"
                "• No hazardous materials without approval"
            ),
            "move_in_checklist": [
                "Provide Certificate of Insurance (COI)",
                "Submit business license copy",
                "Register authorized personnel",
                "Schedule loading dock for move-in",
                "Coordinate IT/telecom setup",
                "Review building emergency procedures",
                "Obtain parking passes",
                "Schedule building orientation",
            ],
            "invitation_email_subject": "Complete Your Commercial Lease Setup",
            "invitation_email_body": (
                "Dear {{first_name}},\n\n"
                "Please complete the onboarding process for your commercial space "
                "at {{property_name}}: {{link}}\n\n"
                "Required documents:\n"
                "• Certificate of Insurance (General Liability)\n"
                "• Business License\n"
                "• Authorized Contact List\n\n"
                "Our property management team will coordinate move-in logistics "
                "once paperwork is complete.\n\n"
                "{{property_name}} Management"
            ),
            "invitation_sms_body": (
                "Complete your commercial lease setup: {{link}}"
            ),
            "default_fees": [
                {
                    "fee_type": "security_deposit",
                    "name": "Security Deposit",
                    "use_lease_value": True,
                    "lease_field": "security_deposit",
                    "is_required": True,
                    "is_refundable": True,
                },
                {
                    "fee_type": "first_month",
                    "name": "First Month's Rent",
                    "use_lease_value": True,
                    "lease_field": "monthly_rent",
                    "is_required": True,
                    "is_refundable": False,
                },
                {
                    "fee_type": "last_month",
                    "name": "Last Month's Rent",
                    "use_lease_value": True,
                    "lease_field": "monthly_rent",
                    "is_required": True,
                    "is_refundable": False,
                },
                {
                    "fee_type": "key_deposit",
                    "name": "Access Card Deposit",
                    "description": "Per card/fob issued",
                    "amount": "50.00",
                    "is_required": True,
                    "is_refundable": True,
                },
            ],
        },
    ]

    for preset_data in presets:
        OnboardingPreset.objects.create(**preset_data)


def remove_presets(apps, schema_editor):
    """Remove system presets."""
    OnboardingPreset = apps.get_model("tenant_lifecycle", "OnboardingPreset")
    OnboardingPreset.objects.filter(is_system=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("tenant_lifecycle", "0003_add_onboarding_preset"),
    ]

    operations = [
        migrations.RunPython(create_presets, remove_presets),
    ]
