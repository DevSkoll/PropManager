"""
Management command to create comprehensive development data for testing.

Usage:
    python manage.py seed_dev_data          # Create accounts + sample data
    python manage.py seed_dev_data --reset  # Wipe DB and recreate everything

Creates:
    - 15 tenants with various payment scenarios
    - 5 properties with 25+ units
    - 12 months of invoice/payment history
    - Rewards system with streaks and transactions
    - 25+ work orders across all statuses
    - Full communications and documents
"""

import random
import secrets
from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)


# =============================================================================
# Tenant Scenario Definitions
# =============================================================================

TENANT_SCENARIOS = [
    # Perfect Payers (3)
    {
        "username": "perfect_payer",
        "first_name": "Patricia",
        "last_name": "Perfect",
        "email": "patricia.perfect@example.com",
        "scenario": "perfect_payer",
        "description": "12 months of on-time payments",
        "lease_age_months": 12,
        "payment_behavior": "always_on_time",
    },
    {
        "username": "model_tenant",
        "first_name": "Marcus",
        "last_name": "Model",
        "email": "marcus.model@example.com",
        "scenario": "model_tenant",
        "description": "6 months perfect, prepays sometimes",
        "lease_age_months": 8,
        "payment_behavior": "on_time_with_prepayment",
    },
    {
        "username": "reliable_renter",
        "first_name": "Rachel",
        "last_name": "Reliable",
        "email": "rachel.reliable@example.com",
        "scenario": "reliable_payer",
        "description": "Always pays within grace period",
        "lease_age_months": 10,
        "payment_behavior": "within_grace_period",
    },
    # Recovering Tenants (2)
    {
        "username": "recovering_ryan",
        "first_name": "Ryan",
        "last_name": "Recovering",
        "email": "ryan.recovering@example.com",
        "scenario": "broken_streak",
        "description": "Had 6-month streak, broke 2 months ago",
        "lease_age_months": 9,
        "payment_behavior": "recovering",
    },
    {
        "username": "improving_iris",
        "first_name": "Iris",
        "last_name": "Improving",
        "email": "iris.improving@example.com",
        "scenario": "formerly_late",
        "description": "Used to pay late, now on time",
        "lease_age_months": 8,
        "payment_behavior": "improving",
    },
    # Problem Tenants (4)
    {
        "username": "chronic_charlie",
        "first_name": "Charlie",
        "last_name": "Chronic",
        "email": "charlie.chronic@example.com",
        "scenario": "chronic_late",
        "description": "Always 10-20 days late",
        "lease_age_months": 12,
        "payment_behavior": "always_late",
    },
    {
        "username": "overdue_olivia",
        "first_name": "Olivia",
        "last_name": "Overdue",
        "email": "olivia.overdue@example.com",
        "scenario": "overdue_balance",
        "description": "2 months overdue, partial payment",
        "lease_age_months": 6,
        "payment_behavior": "delinquent",
    },
    {
        "username": "struggling_sam",
        "first_name": "Samuel",
        "last_name": "Struggling",
        "email": "sam.struggling@example.com",
        "scenario": "struggling",
        "description": "Sporadic payments, has credit",
        "lease_age_months": 10,
        "payment_behavior": "sporadic",
    },
    {
        "username": "defaulting_dana",
        "first_name": "Dana",
        "last_name": "Default",
        "email": "dana.default@example.com",
        "scenario": "recent_default",
        "description": "Was good, current month unpaid",
        "lease_age_months": 11,
        "payment_behavior": "recent_default",
    },
    # New Tenants (3)
    {
        "username": "newbie_nick",
        "first_name": "Nicholas",
        "last_name": "Newbie",
        "email": "nick.newbie@example.com",
        "scenario": "new_1_month",
        "description": "Just moved in last month",
        "lease_age_months": 1,
        "payment_behavior": "on_time",
    },
    {
        "username": "recent_rita",
        "first_name": "Rita",
        "last_name": "Recent",
        "email": "rita.recent@example.com",
        "scenario": "new_3_months",
        "description": "3 months in, perfect so far",
        "lease_age_months": 3,
        "payment_behavior": "on_time",
    },
    {
        "username": "fresh_frank",
        "first_name": "Frank",
        "last_name": "Fresh",
        "email": "frank.fresh@example.com",
        "scenario": "new_unpaid",
        "description": "First invoice still pending",
        "lease_age_months": 1,
        "payment_behavior": "pending",
    },
    # Special Scenarios (3)
    {
        "username": "prepay_paula",
        "first_name": "Paula",
        "last_name": "Prepay",
        "email": "paula.prepay@example.com",
        "scenario": "advance_payer",
        "description": "Pays months in advance",
        "lease_age_months": 12,
        "payment_behavior": "prepays",
    },
    {
        "username": "corporate_carl",
        "first_name": "Carl",
        "last_name": "Corporate",
        "email": "carl.corporate@example.com",
        "scenario": "corporate_tenant",
        "description": "Company pays via ACH",
        "lease_age_months": 10,
        "payment_behavior": "ach_autopay",
    },
    {
        "username": "crypto_cathy",
        "first_name": "Catherine",
        "last_name": "Crypto",
        "email": "cathy.crypto@example.com",
        "scenario": "crypto_payer",
        "description": "Pays in Bitcoin occasionally",
        "lease_age_months": 6,
        "payment_behavior": "mixed_crypto",
    },
]


class Command(BaseCommand):
    help = "Seed the database with comprehensive development data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Flush the database before seeding",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write(self.style.WARNING("Flushing database..."))
            from django.core.management import call_command
            call_command("flush", "--no-input")

        self._create_users()
        self._create_properties()
        self._create_leases()
        self._create_billing_config()
        self._create_utility_configs()
        self._create_invoices()
        self._create_rewards_system()
        self._create_work_orders()
        self._create_communications()
        self._create_document_categories()
        self._create_document_folders_and_documents()

        self.stdout.write(self.style.SUCCESS("\nDevelopment data seeded successfully!"))
        self._print_summary()
        self._print_accounts()

    # =========================================================================
    # Users
    # =========================================================================

    def _create_users(self):
        from apps.accounts.models import User, TenantProfile, AdminProfile

        self.stdout.write("Creating user accounts...")

        # Admin / Landlord
        self.admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@propmanager.com",
                "first_name": "Alex",
                "last_name": "Manager",
                "role": "admin",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        self.admin_user.set_password("admin123")
        self.admin_user.role = "admin"
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.save()
        AdminProfile.objects.get_or_create(
            user=self.admin_user,
            defaults={"otp_enabled": False},
        )
        self.stdout.write(f"  {'Created' if created else 'Updated'}: admin (Admin/Landlord)")

        # Staff user
        self.staff_user, created = User.objects.get_or_create(
            username="staff",
            defaults={
                "email": "staff@propmanager.com",
                "first_name": "Sam",
                "last_name": "Staff",
                "role": "staff",
                "is_staff": True,
            },
        )
        self.staff_user.set_password("staff123")
        self.staff_user.role = "staff"
        self.staff_user.is_staff = True
        self.staff_user.save()
        AdminProfile.objects.get_or_create(
            user=self.staff_user,
            defaults={"otp_enabled": False},
        )
        self.stdout.write(f"  {'Created' if created else 'Updated'}: staff (Staff)")

        # Create tenants from scenarios
        self.tenants = []
        self.tenant_scenarios = {}

        for scenario in TENANT_SCENARIOS:
            phone = f"+1555{random.randint(1000000, 9999999)}"
            user, created = User.objects.get_or_create(
                username=scenario["username"],
                defaults={
                    "email": scenario["email"],
                    "first_name": scenario["first_name"],
                    "last_name": scenario["last_name"],
                    "role": "tenant",
                    "phone_number": phone,
                    "is_email_verified": True,
                    "is_phone_verified": True,
                },
            )
            user.set_password("tenant123")
            user.role = "tenant"
            user.save()

            TenantProfile.objects.get_or_create(
                user=user,
                defaults={
                    "emergency_contact_name": f"{scenario['first_name']}'s Emergency Contact",
                    "emergency_contact_phone": phone.replace("555", "556"),
                    "move_in_date": date.today() - timedelta(days=scenario["lease_age_months"] * 30),
                },
            )
            self.tenants.append(user)
            self.tenant_scenarios[user.username] = scenario
            self.stdout.write(f"  {'Created' if created else 'Updated'}: {user.username} ({scenario['scenario']})")

    # =========================================================================
    # Properties and Units
    # =========================================================================

    def _create_properties(self):
        from apps.properties.models import Property, Unit, Amenity

        self.stdout.write("Creating properties and units...")

        # Property definitions
        props_data = [
            {
                "name": "Sunset Apartments",
                "type": "apartment",
                "address": "100 Sunset Blvd",
                "city": "Los Angeles",
                "state": "CA",
                "zip": "90028",
                "units": 10,
                "manager_name": "Alex Manager",
                "manager_email": "alex@sunsetapts.com",
                "manager_phone": "+15551234567",
                "office_hours": "Mon-Fri 9am-5pm",
            },
            {
                "name": "Maple Grove Townhomes",
                "type": "townhouse",
                "address": "250 Maple Ave",
                "city": "Portland",
                "state": "OR",
                "zip": "97201",
                "units": 6,
                "manager_name": "Morgan Grove",
                "manager_email": "morgan@maplegrove.com",
                "manager_phone": "+15559876543",
                "office_hours": "Mon-Sat 10am-6pm",
            },
            {
                "name": "Oak Street House",
                "type": "single_family",
                "address": "42 Oak Street",
                "city": "Austin",
                "state": "TX",
                "zip": "78701",
                "units": 1,
            },
            {
                "name": "Downtown Lofts",
                "type": "condo",
                "address": "555 Main Street",
                "city": "Denver",
                "state": "CO",
                "zip": "80202",
                "units": 8,
                "manager_name": "Dana Downtown",
                "manager_email": "dana@downtownlofts.com",
                "manager_phone": "+15557654321",
                "office_hours": "Mon-Fri 8am-6pm",
            },
            {
                "name": "Riverside Commons",
                "type": "multi_family",
                "address": "789 River Road",
                "city": "Chicago",
                "state": "IL",
                "zip": "60601",
                "units": 4,
            },
        ]

        self.properties = []
        self.units = []

        for pdata in props_data:
            prop, created = Property.objects.get_or_create(
                name=pdata["name"],
                defaults={
                    "property_type": pdata["type"],
                    "address_line1": pdata["address"],
                    "city": pdata["city"],
                    "state": pdata["state"],
                    "zip_code": pdata["zip"],
                    "total_units": pdata["units"],
                    "is_active": True,
                    "created_by": self.admin_user,
                    "manager_name": pdata.get("manager_name", ""),
                    "manager_email": pdata.get("manager_email", ""),
                    "manager_phone": pdata.get("manager_phone", ""),
                    "office_hours": pdata.get("office_hours", ""),
                },
            )
            self.properties.append(prop)
            self.stdout.write(f"  {'Created' if created else 'Exists'}: {pdata['name']}")

        # Create units for each property
        unit_configs = [
            # Sunset Apartments (10 units)
            (0, "101", 1, "1.0", 650, 1200, "occupied"),
            (0, "102", 1, "1.0", 650, 1250, "occupied"),
            (0, "103", 1, "1.0", 700, 1300, "occupied"),
            (0, "104", 2, "1.0", 850, 1500, "occupied"),
            (0, "105", 2, "1.5", 900, 1600, "occupied"),
            (0, "201", 2, "1.5", 950, 1700, "occupied"),
            (0, "202", 2, "2.0", 1000, 1800, "occupied"),
            (0, "203", 3, "2.0", 1200, 2200, "occupied"),
            (0, "204", 3, "2.0", 1200, 2200, "vacant"),
            (0, "205", 1, "1.0", 600, 1100, "maintenance"),
            # Maple Grove Townhomes (6 units)
            (1, "TH-1", 3, "2.5", 1400, 2200, "occupied"),
            (1, "TH-2", 3, "2.5", 1450, 2300, "occupied"),
            (1, "TH-3", 3, "2.5", 1400, 2200, "occupied"),
            (1, "TH-4", 4, "3.0", 1800, 2800, "occupied"),
            (1, "TH-5", 4, "3.0", 1850, 2900, "vacant"),
            (1, "TH-6", 3, "2.5", 1400, 2200, "maintenance"),
            # Oak Street House (1 unit)
            (2, "A", 4, "2.0", 1800, 2500, "occupied"),
            # Downtown Lofts (8 units)
            (3, "L1", 1, "1.0", 800, 1800, "occupied"),
            (3, "L2", 1, "1.0", 850, 1850, "vacant"),
            (3, "L3", 2, "1.0", 1000, 2100, "occupied"),
            (3, "L4", 2, "1.5", 1100, 2300, "occupied"),
            (3, "L5", 2, "1.5", 1100, 2300, "vacant"),
            (3, "L6", 3, "2.0", 1400, 2800, "vacant"),
            (3, "P1", 1, "1.0", 600, 1500, "occupied"),  # Penthouse studio
            (3, "P2", 2, "2.0", 1200, 3000, "vacant"),  # Penthouse 2br
            # Riverside Commons (4 units)
            (4, "RC-1", 2, "1.0", 950, 1600, "occupied"),
            (4, "RC-2", 2, "1.0", 950, 1600, "vacant"),
            (4, "RC-3", 3, "1.5", 1100, 1900, "occupied"),
            (4, "RC-4", 3, "1.5", 1100, 1900, "vacant"),
        ]

        for prop_idx, unit_num, beds, baths, sqft, rent, status in unit_configs:
            unit, _ = Unit.objects.get_or_create(
                property=self.properties[prop_idx],
                unit_number=unit_num,
                defaults={
                    "bedrooms": beds,
                    "bathrooms": Decimal(baths),
                    "square_feet": sqft,
                    "base_rent": Decimal(str(rent)),
                    "status": status,
                    "floor": 1 if "-" not in unit_num else int(unit_num[0]) if unit_num[0].isdigit() else 1,
                },
            )
            self.units.append(unit)

        # Amenities
        amenity_names = [
            ("In-Unit Washer/Dryer", "bi-tsunami"),
            ("Dishwasher", "bi-droplet"),
            ("Central AC", "bi-snow"),
            ("Parking Spot", "bi-car-front"),
            ("Balcony", "bi-sun"),
            ("Pet Friendly", "bi-heart"),
            ("Gym Access", "bi-activity"),
            ("Pool Access", "bi-water"),
            ("Storage Unit", "bi-box"),
            ("Rooftop Deck", "bi-building"),
        ]
        for name, icon in amenity_names:
            Amenity.objects.get_or_create(name=name, defaults={"icon": icon})

        self.stdout.write(f"  Created {len(self.units)} units across {len(self.properties)} properties")

    # =========================================================================
    # Leases
    # =========================================================================

    def _create_leases(self):
        from apps.leases.models import (
            Lease, LeaseTerm, LeaseOccupant, LeasePet, LeaseFee, LeaseSignature, LeaseTermination
        )

        self.stdout.write("Creating leases...")

        self.leases = []
        today = date.today()

        # Map tenants to units (first 15 occupied units)
        occupied_units = [u for u in self.units if u.status == "occupied"]

        for i, tenant in enumerate(self.tenants):
            if i >= len(occupied_units):
                break

            unit = occupied_units[i]
            scenario = self.tenant_scenarios[tenant.username]
            lease_months = scenario["lease_age_months"]

            # Determine lease status and dates
            start_date = today - relativedelta(months=lease_months)
            end_date = start_date + relativedelta(months=12)

            # Most leases are active, some variations
            status = "active"
            signature_status = "executed"

            if scenario["scenario"] == "new_unpaid":
                signature_status = "pending"  # New tenant, not signed yet

            lease, created = Lease.objects.get_or_create(
                unit=unit,
                tenant=tenant,
                status=status,
                defaults={
                    "lease_type": "fixed" if lease_months > 2 else "month_to_month",
                    "start_date": start_date,
                    "end_date": end_date,
                    "monthly_rent": unit.base_rent,
                    "security_deposit": unit.base_rent,
                    "rent_due_day": 1,
                    "grace_period_days": 5,
                    "late_fee_amount": Decimal("50.00"),
                    "late_fee_type": "flat",
                    "max_occupants": 2 + (i % 3),
                    "pets_allowed": i % 3 != 2,
                    "max_pets": 2 if i % 3 != 2 else 0,
                    "smoking_allowed": False,
                    "subletting_allowed": False,
                    "renters_insurance_required": True,
                    "renters_insurance_minimum": Decimal("100000.00"),
                    "parking_spaces": 1 if i % 2 == 0 else 0,
                    "auto_renewal": i % 4 == 0,
                    "signature_status": signature_status,
                    "fully_executed_at": timezone.now() - timedelta(days=lease_months * 30) if signature_status == "executed" else None,
                    "created_by": self.admin_user,
                },
            )
            self.leases.append(lease)

            if created:
                # Add standard lease terms
                terms = [
                    ("Quiet Hours", "Quiet hours are from 10:00 PM to 8:00 AM. Please be respectful of neighbors."),
                    ("Maintenance Requests", "All maintenance requests should be submitted through the tenant portal."),
                    ("Rent Payment", f"Rent is due on the {lease.rent_due_day}st of each month. A late fee of ${lease.late_fee_amount} applies after {lease.grace_period_days} days."),
                ]
                for title, desc in terms:
                    LeaseTerm.objects.get_or_create(
                        lease=lease, title=title,
                        defaults={"description": desc, "is_standard": True}
                    )

                # Add occupants for some leases
                if i % 3 == 0:  # Family
                    LeaseOccupant.objects.create(
                        lease=lease,
                        first_name=fake.first_name(),
                        last_name=tenant.last_name,
                        relationship="spouse",
                        email=fake.email(),
                        is_on_lease=True,
                    )
                elif i % 5 == 0:  # Roommate
                    LeaseOccupant.objects.create(
                        lease=lease,
                        first_name=fake.first_name(),
                        last_name=fake.last_name(),
                        relationship="roommate",
                        email=fake.email(),
                        is_on_lease=True,
                    )

                # Add pets for some leases
                if lease.pets_allowed and i % 2 == 0:
                    pet_types = [
                        ("dog", "Max", "Golden Retriever", 65),
                        ("cat", "Whiskers", "Tabby", 10),
                        ("dog", "Bella", "Labrador", 70),
                    ]
                    pet = pet_types[i % 3]
                    LeasePet.objects.create(
                        lease=lease,
                        pet_type=pet[0],
                        name=pet[1],
                        breed=pet[2],
                        weight_lbs=Decimal(str(pet[3])),
                        vaccination_current=True,
                        pet_deposit=Decimal("300.00"),
                        monthly_pet_rent=Decimal("35.00"),
                    )

                # Add fees
                LeaseFee.objects.create(
                    lease=lease,
                    fee_type="admin",
                    name="Administrative Fee",
                    amount=Decimal("150.00"),
                    frequency="one_time",
                )
                if lease.parking_spaces > 0:
                    LeaseFee.objects.create(
                        lease=lease,
                        fee_type="parking",
                        name="Reserved Parking",
                        amount=Decimal("75.00"),
                        frequency="monthly",
                    )

                # Add signature for executed leases
                if signature_status == "executed":
                    LeaseSignature.objects.create(
                        lease=lease,
                        signer_type="tenant",
                        signer_name=tenant.get_full_name(),
                        signer_email=tenant.email,
                        signer_user=tenant,
                        signed_at=timezone.now() - timedelta(days=lease_months * 30),
                        ip_address="192.168.1.100",
                        signing_token=secrets.token_urlsafe(32),
                    )
                    LeaseSignature.objects.create(
                        lease=lease,
                        signer_type="landlord",
                        signer_name="Alex Manager",
                        signer_email="admin@propmanager.com",
                        signer_user=self.admin_user,
                        signed_at=timezone.now() - timedelta(days=lease_months * 30 - 1),
                        ip_address="192.168.1.1",
                        signing_token=secrets.token_urlsafe(32),
                    )

            self.stdout.write(f"  {'Created' if created else 'Exists'}: {tenant.get_full_name()} @ {unit}")

        # Create some historical leases (expired/terminated)
        self._create_historical_leases()

    def _create_historical_leases(self):
        from apps.leases.models import Lease, LeaseTermination

        # Find vacant units for historical leases
        vacant_units = [u for u in self.units if u.status == "vacant"][:3]

        for i, unit in enumerate(vacant_units):
            # Create a past tenant user for this lease
            past_tenant = None
            # Just reference an expired lease without a tenant for simplicity
            start_date = date.today() - relativedelta(months=18 + i * 3)
            end_date = start_date + relativedelta(months=12)

            if i == 0:
                # Expired lease
                status = "expired"
                term_reason = None
            else:
                # Terminated lease
                status = "terminated"
                term_reason = "Job relocation" if i == 1 else "Family emergency"

            # We'll skip creating historical leases without users to avoid complexity
            self.stdout.write(f"  Skipping historical lease for {unit} (would need historical tenant)")

    # =========================================================================
    # Billing Configuration
    # =========================================================================

    def _create_billing_config(self):
        from apps.billing.models import PropertyBillingConfig

        self.stdout.write("Creating billing configurations...")

        configs = [
            {
                "property": self.properties[0],  # Sunset Apartments
                "auto_generate_invoices": True,
                "default_due_day": 1,
                "late_fee_enabled": True,
                "grace_period_days": 5,
                "late_fee_type": "flat",
                "late_fee_amount": Decimal("50.00"),
                "late_fee_frequency": "one_time",
                "late_fee_cap": Decimal("200.00"),
            },
            {
                "property": self.properties[1],  # Maple Grove
                "auto_generate_invoices": True,
                "default_due_day": 1,
                "late_fee_enabled": True,
                "grace_period_days": 3,
                "late_fee_type": "percentage",
                "late_fee_amount": Decimal("5.00"),  # 5%
                "late_fee_frequency": "one_time",
            },
            {
                "property": self.properties[2],  # Oak Street
                "auto_generate_invoices": True,
                "default_due_day": 1,
                "late_fee_enabled": True,
                "grace_period_days": 5,
                "late_fee_type": "flat",
                "late_fee_amount": Decimal("75.00"),
                "late_fee_frequency": "recurring_monthly",
                "late_fee_cap": Decimal("300.00"),
            },
            {
                "property": self.properties[3],  # Downtown Lofts
                "auto_generate_invoices": True,
                "default_due_day": 1,
                "late_fee_enabled": True,
                "grace_period_days": 5,
                "late_fee_type": "flat",
                "late_fee_amount": Decimal("100.00"),
                "late_fee_frequency": "one_time",
            },
            {
                "property": self.properties[4],  # Riverside Commons
                "auto_generate_invoices": True,
                "default_due_day": 1,
                "late_fee_enabled": False,  # No late fees
            },
        ]

        for cfg in configs:
            PropertyBillingConfig.objects.get_or_create(
                property=cfg["property"],
                defaults={
                    "auto_generate_invoices": cfg.get("auto_generate_invoices", True),
                    "default_due_day": cfg.get("default_due_day", 1),
                    "late_fee_enabled": cfg.get("late_fee_enabled", False),
                    "grace_period_days": cfg.get("grace_period_days", 5),
                    "late_fee_type": cfg.get("late_fee_type", "flat"),
                    "late_fee_amount": cfg.get("late_fee_amount", Decimal("0")),
                    "late_fee_frequency": cfg.get("late_fee_frequency", "one_time"),
                    "late_fee_cap": cfg.get("late_fee_cap", Decimal("0")),
                },
            )

        self.stdout.write(f"  Created {len(configs)} billing configurations")

    # =========================================================================
    # Utility Configs
    # =========================================================================

    def _create_utility_configs(self):
        from apps.billing.models import UtilityConfig

        self.stdout.write("Creating utility configurations...")

        # Get all occupied units with leases
        occupied_units = [u for u in self.units if u.status == "occupied"]

        created_count = 0
        for unit in occupied_units:
            # Standard utilities for each unit
            utilities = [
                ("water", "fixed", Decimal("45.00")),
                ("electric", "variable", Decimal(str(random.randint(80, 150)))),
                ("trash", "fixed", Decimal("25.00")),
            ]

            # Some units have gas
            if random.random() > 0.5:
                utilities.append(("gas", "fixed", Decimal(str(random.randint(30, 60)))))

            for utype, mode, rate in utilities:
                _, created = UtilityConfig.objects.get_or_create(
                    unit=unit,
                    utility_type=utype,
                    defaults={
                        "billing_mode": mode,
                        "rate": rate,
                        "is_active": True,
                    },
                )
                if created:
                    created_count += 1

        self.stdout.write(f"  Created {created_count} utility configurations")

    # =========================================================================
    # Invoices and Payments
    # =========================================================================

    def _create_invoices(self):
        from apps.billing.models import Invoice, InvoiceLineItem, Payment, PrepaymentCredit

        self.stdout.write("Creating invoices and payments (12 months history)...")

        today = date.today()
        invoice_count = 0
        payment_count = 0

        for lease in self.leases:
            tenant = lease.tenant
            scenario = self.tenant_scenarios.get(tenant.username, {})
            payment_behavior = scenario.get("payment_behavior", "on_time")
            lease_months = scenario.get("lease_age_months", 12)

            # Generate invoices for each month of the lease
            for month_offset in range(lease_months, 0, -1):
                invoice_date = today - relativedelta(months=month_offset)
                invoice_date = invoice_date.replace(day=1)
                due_date = invoice_date.replace(day=5)

                inv_num = f"INV-{invoice_date.strftime('%Y%m')}-{lease.pk.hex[:4].upper()}"

                # Determine invoice status based on scenario
                if month_offset == 1 and payment_behavior == "pending":
                    status = "issued"
                    amount_paid = Decimal("0")
                elif month_offset <= 2 and payment_behavior == "delinquent":
                    status = "overdue" if month_offset == 2 else "partial"
                    amount_paid = lease.monthly_rent * Decimal("0.5") if month_offset == 1 else Decimal("0")
                elif month_offset == 1 and payment_behavior == "recent_default":
                    status = "overdue"
                    amount_paid = Decimal("0")
                else:
                    status = "paid"
                    amount_paid = lease.monthly_rent

                invoice, created = Invoice.objects.get_or_create(
                    invoice_number=inv_num,
                    defaults={
                        "lease": lease,
                        "tenant": tenant,
                        "status": status,
                        "issue_date": invoice_date,
                        "due_date": due_date,
                        "total_amount": lease.monthly_rent,
                        "amount_paid": amount_paid,
                        "created_by": self.admin_user,
                    },
                )

                if created:
                    invoice_count += 1

                    # Add line items
                    InvoiceLineItem.objects.create(
                        invoice=invoice,
                        charge_type="rent",
                        description=f"Monthly Rent - {invoice_date.strftime('%B %Y')}",
                        quantity=1,
                        unit_price=lease.monthly_rent,
                        amount=lease.monthly_rent,
                    )

                    # Create payment if paid
                    if status == "paid":
                        # Determine payment timing
                        if payment_behavior == "always_on_time":
                            pay_date = due_date - timedelta(days=random.randint(1, 4))
                        elif payment_behavior == "within_grace_period":
                            pay_date = due_date + timedelta(days=random.randint(1, 4))
                        elif payment_behavior == "always_late":
                            pay_date = due_date + timedelta(days=random.randint(10, 20))
                        elif payment_behavior == "ach_autopay":
                            pay_date = due_date
                        else:
                            pay_date = due_date - timedelta(days=random.randint(0, 3))

                        # Choose payment method
                        if payment_behavior == "ach_autopay":
                            method = "ach"
                        elif payment_behavior == "mixed_crypto" and random.random() > 0.7:
                            method = "crypto"
                        else:
                            method = random.choices(
                                ["online", "ach", "check", "cash"],
                                weights=[60, 25, 10, 5]
                            )[0]

                        Payment.objects.create(
                            tenant=tenant,
                            invoice=invoice,
                            amount=lease.monthly_rent,
                            method=method,
                            status="completed",
                            reference_number=f"PAY-{random.randint(100000, 999999)}",
                            payment_date=timezone.make_aware(
                                timezone.datetime.combine(pay_date, timezone.datetime.min.time())
                            ),
                        )
                        payment_count += 1

                    elif status == "partial":
                        Payment.objects.create(
                            tenant=tenant,
                            invoice=invoice,
                            amount=amount_paid,
                            method="online",
                            status="completed",
                            reference_number=f"PAY-{random.randint(100000, 999999)}",
                        )
                        payment_count += 1

        # Create prepayment credits for advance_payer
        for tenant in self.tenants:
            scenario = self.tenant_scenarios.get(tenant.username, {})
            if scenario.get("payment_behavior") == "prepays":
                PrepaymentCredit.objects.get_or_create(
                    tenant=tenant,
                    reason="Overpayment on invoice",
                    defaults={
                        "amount": Decimal("500.00"),
                        "remaining_amount": Decimal("350.00"),
                    },
                )

        self.stdout.write(f"  Created {invoice_count} invoices, {payment_count} payments")

    # =========================================================================
    # Rewards System
    # =========================================================================

    def _create_rewards_system(self):
        from apps.rewards.models import (
            PropertyRewardsConfig, StreakRewardTier, RewardBalance,
            RewardTransaction, StreakEvaluation
        )

        self.stdout.write("Creating rewards system data...")

        # Configure rewards for properties
        rewards_configs = [
            {
                "property": self.properties[0],  # Sunset Apartments
                "rewards_enabled": True,
                "streak_reward_enabled": True,
                "prepayment_reward_enabled": True,
                "prepayment_threshold_amount": Decimal("500.00"),
                "prepayment_reward_amount": Decimal("25.00"),
                "auto_apply_rewards": True,
                "tiers": [
                    (3, Decimal("25.00"), False),
                    (6, Decimal("50.00"), False),
                    (12, Decimal("100.00"), True),
                ],
            },
            {
                "property": self.properties[1],  # Maple Grove
                "rewards_enabled": True,
                "streak_reward_enabled": True,
                "prepayment_reward_enabled": False,
                "tiers": [
                    (6, Decimal("75.00"), False),
                ],
            },
            {
                "property": self.properties[2],  # Oak Street
                "rewards_enabled": False,
            },
            {
                "property": self.properties[3],  # Downtown Lofts
                "rewards_enabled": True,
                "streak_reward_enabled": True,
                "prepayment_reward_enabled": True,
                "prepayment_threshold_amount": Decimal("1000.00"),
                "prepayment_reward_amount": Decimal("50.00"),
                "tiers": [
                    (3, Decimal("30.00"), False),
                    (6, Decimal("60.00"), False),
                ],
            },
        ]

        for cfg in rewards_configs:
            config, created = PropertyRewardsConfig.objects.get_or_create(
                property=cfg["property"],
                defaults={
                    "rewards_enabled": cfg.get("rewards_enabled", False),
                    "streak_reward_enabled": cfg.get("streak_reward_enabled", False),
                    "prepayment_reward_enabled": cfg.get("prepayment_reward_enabled", False),
                    "prepayment_threshold_amount": cfg.get("prepayment_threshold_amount", Decimal("0")),
                    "prepayment_reward_amount": cfg.get("prepayment_reward_amount", Decimal("0")),
                    "auto_apply_rewards": cfg.get("auto_apply_rewards", False),
                },
            )

            # Create tiers
            for months, amount, recurring in cfg.get("tiers", []):
                StreakRewardTier.objects.get_or_create(
                    config=config,
                    months_required=months,
                    defaults={
                        "reward_amount": amount,
                        "is_recurring": recurring,
                    },
                )

        # Create reward balances and transactions for eligible tenants
        for tenant in self.tenants:
            scenario = self.tenant_scenarios.get(tenant.username, {})
            behavior = scenario.get("payment_behavior", "")

            if behavior in ["always_on_time", "on_time_with_prepayment", "within_grace_period", "prepays"]:
                # Calculate rewards based on streak
                lease_months = scenario.get("lease_age_months", 0)

                balance = Decimal("0")
                total_earned = Decimal("0")

                # Perfect payers get full rewards
                if behavior == "always_on_time" and lease_months >= 12:
                    total_earned = Decimal("175.00")  # 25 + 50 + 100
                    balance = Decimal("125.00")  # Some redeemed
                elif behavior == "on_time_with_prepayment" and lease_months >= 6:
                    total_earned = Decimal("100.00")  # 25 + 50 + prepayment
                    balance = Decimal("75.00")
                elif lease_months >= 3:
                    total_earned = Decimal("25.00")
                    balance = Decimal("25.00")

                if total_earned > 0:
                    rb, _ = RewardBalance.objects.get_or_create(
                        tenant=tenant,
                        defaults={
                            "balance": balance,
                            "total_earned": total_earned,
                            "total_redeemed": total_earned - balance,
                        },
                    )

                    # Create streak evaluation
                    lease = next((l for l in self.leases if l.tenant == tenant), None)
                    if lease:
                        config = PropertyRewardsConfig.objects.filter(
                            property=lease.unit.property
                        ).first()
                        if config:
                            StreakEvaluation.objects.get_or_create(
                                tenant=tenant,
                                config=config,
                                defaults={
                                    "current_streak_months": min(lease_months, 12),
                                    "last_evaluated_month": date.today().replace(day=1),
                                },
                            )

                    # Create sample transactions
                    if total_earned >= 25:
                        RewardTransaction.objects.get_or_create(
                            tenant=tenant,
                            transaction_type="streak_earned",
                            amount=Decimal("25.00"),
                            defaults={
                                "balance_after": Decimal("25.00"),
                                "description": "3-month on-time payment streak reward",
                                "created_by": self.admin_user,
                            },
                        )

        self.stdout.write("  Created rewards configs, tiers, balances, and transactions")

    # =========================================================================
    # Work Orders
    # =========================================================================

    def _create_work_orders(self):
        from apps.workorders.models import WorkOrder, WorkOrderNote, ContractorAssignment

        self.stdout.write("Creating work orders...")

        # Work order definitions covering all statuses and categories
        wo_definitions = [
            # Created (3)
            ("created", "medium", "plumbing", "Slow draining bathtub", "The bathtub takes 10+ minutes to drain after a shower."),
            ("created", "emergency", "hvac", "No heat in unit", "Heating system not working, temperature dropping to 55F."),
            ("created", "low", "general", "Closet door off track", "Sliding closet door came off its track."),
            # Verified (3)
            ("verified", "high", "electrical", "Flickering lights in kitchen", "All kitchen lights flicker intermittently. Possible wiring issue."),
            ("verified", "medium", "plumbing", "Leaky faucet in bathroom", "Bathroom sink faucet drips constantly."),
            ("verified", "low", "landscaping", "Overgrown bushes blocking walkway", "Front bushes need trimming."),
            # Assigned (4)
            ("assigned", "high", "appliance", "Refrigerator not cooling", "Refrigerator temperature stays at 50F despite settings."),
            ("assigned", "medium", "hvac", "AC making loud noise", "Air conditioner makes grinding sound when running."),
            ("assigned", "medium", "electrical", "Outlet not working", "Living room outlet has no power."),
            ("assigned", "low", "cleaning", "Carpet stain in hallway", "Large stain in common hallway carpet."),
            # In Progress (4)
            ("in_progress", "high", "plumbing", "Water heater leaking", "Small puddle forming under water heater."),
            ("in_progress", "medium", "structural", "Crack in ceiling", "Hairline crack appearing in bedroom ceiling."),
            ("in_progress", "medium", "appliance", "Dishwasher not draining", "Water remains after wash cycle."),
            ("in_progress", "emergency", "pest_control", "Mouse sighting in unit", "Tenant spotted mouse in kitchen."),
            # Completed (5)
            ("completed", "medium", "plumbing", "Running toilet", "Toilet runs continuously."),
            ("completed", "high", "electrical", "Circuit breaker tripping", "Kitchen circuit trips when microwave runs."),
            ("completed", "low", "general", "Squeaky door hinges", "Bedroom door squeaks loudly."),
            ("completed", "medium", "appliance", "Garbage disposal jammed", "Disposal making humming noise but not working."),
            ("completed", "high", "hvac", "Thermostat not responding", "Digital thermostat screen is blank."),
            # Closed (6)
            ("closed", "emergency", "plumbing", "Burst pipe in bathroom", "Pipe burst under sink, water damage."),
            ("closed", "high", "electrical", "Smoke detector malfunction", "Smoke detector beeping continuously."),
            ("closed", "medium", "appliance", "Oven not heating", "Oven stays cold even at max temperature."),
            ("closed", "medium", "structural", "Window won't close", "Bedroom window stuck open."),
            ("closed", "low", "landscaping", "Dead plant replacement", "Planter box has dead plants."),
            ("closed", "low", "other", "Mailbox key replacement", "Tenant lost mailbox key."),
        ]

        occupied_units = [u for u in self.units if u.status == "occupied"]
        wo_count = 0

        for i, (status, priority, category, title, desc) in enumerate(wo_definitions):
            unit = occupied_units[i % len(occupied_units)]
            tenant = next((l.tenant for l in self.leases if l.unit == unit), None)

            wo, created = WorkOrder.objects.get_or_create(
                title=title,
                unit=unit,
                defaults={
                    "description": desc,
                    "reported_by": tenant,
                    "status": status,
                    "priority": priority,
                    "category": category,
                    "scheduled_date": date.today() + timedelta(days=random.randint(-30, 14)),
                    "cost_estimate": Decimal(str(random.randint(50, 500))),
                    "created_by": tenant or self.admin_user,
                },
            )

            if created:
                wo_count += 1

                # Add contractor for assigned/in_progress/completed/closed
                if status in ("assigned", "in_progress", "completed", "closed"):
                    ContractorAssignment.objects.create(
                        work_order=wo,
                        contractor_name=fake.company() + " Services",
                        contractor_phone=f"+1555{random.randint(1000000, 9999999)}",
                        contractor_email=fake.company_email(),
                    )

                # Add notes
                WorkOrderNote.objects.create(
                    work_order=wo,
                    author_user=tenant,
                    text=f"Reported: {desc}",
                    is_internal=False,
                )

                if status in ("verified", "assigned", "in_progress", "completed", "closed"):
                    WorkOrderNote.objects.create(
                        work_order=wo,
                        author_user=self.staff_user,
                        text="Work order reviewed and verified.",
                        is_internal=True,
                    )

                if status in ("completed", "closed"):
                    wo.actual_cost = Decimal(str(random.randint(50, 400)))
                    wo.completed_date = date.today() - timedelta(days=random.randint(1, 30))
                    wo.save()

                    WorkOrderNote.objects.create(
                        work_order=wo,
                        author_user=self.admin_user,
                        text="Work completed successfully.",
                        is_internal=False,
                    )

        self.stdout.write(f"  Created {wo_count} work orders")

    # =========================================================================
    # Communications
    # =========================================================================

    def _create_communications(self):
        from apps.communications.models import Announcement, MessageThread, Message, Notification

        self.stdout.write("Creating communications...")

        # Announcements
        announcements = [
            ("Building Maintenance Notice", "Water will be shut off Friday 9 AM - 12 PM for scheduled pipe maintenance.", self.properties[0], True, 2),
            ("Holiday Office Hours", "Management office closed Monday for the holiday. For emergencies, call maintenance hotline.", None, True, 5),
            ("Parking Lot Restriping", "Parking lot will be restriped this Saturday. Please move vehicles by 7 AM.", self.properties[0], True, 7),
            ("New Online Portal Features", "We've added new features to the tenant portal including rewards tracking and document uploads.", None, True, 14),
            ("Community BBQ", "Join us for a community BBQ on the 4th! Food and drinks provided.", self.properties[0], True, 21),
            ("Snow Removal Reminder", "Please move vehicles during snow events to allow plowing.", self.properties[1], True, 30),
            ("Rent Increase Notice - Draft", "Annual rent increase effective March 1st.", self.properties[0], False, 1),
            ("Pool Opening", "Community pool opens Memorial Day weekend!", self.properties[3], True, 45),
        ]

        for title, body, prop, published, days_ago in announcements:
            Announcement.objects.get_or_create(
                title=title,
                defaults={
                    "body": body,
                    "author": self.admin_user,
                    "property": prop,
                    "is_published": published,
                    "published_at": timezone.now() - timedelta(days=days_ago) if published else None,
                },
            )

        # Message threads
        for i, tenant in enumerate(self.tenants[:5]):
            subjects = [
                "Question about rent payment",
                "Parking spot inquiry",
                "Lease renewal discussion",
                "Package delivery concern",
                "Utility billing question",
            ]
            thread, created = MessageThread.objects.get_or_create(
                subject=subjects[i % len(subjects)],
            )
            if created:
                thread.participants.add(tenant, self.admin_user)
                Message.objects.create(
                    thread=thread,
                    sender=tenant,
                    body=f"Hi, I had a question about {subjects[i % len(subjects)].lower()}. Can you help?",
                )
                Message.objects.create(
                    thread=thread,
                    sender=self.admin_user,
                    body="Of course! I'd be happy to help. Could you provide more details?",
                )

        # Notifications
        notification_types = [
            ("billing", "Rent Due Reminder", "Your rent for this month is due in 5 days."),
            ("billing", "Payment Received", "Your payment of ${amount} has been received."),
            ("work_order", "Work Order Update", "Your work order has been assigned to a contractor."),
            ("lease", "Lease Expiring", "Your lease expires in 60 days. Contact us to discuss renewal."),
            ("announcement", "New Announcement", "There's a new building announcement."),
            ("system", "Profile Updated", "Your contact information has been updated."),
        ]

        for tenant in self.tenants[:8]:
            notif_type = notification_types[self.tenants.index(tenant) % len(notification_types)]
            Notification.objects.get_or_create(
                recipient=tenant,
                title=notif_type[1],
                defaults={
                    "channel": "in_app",
                    "category": notif_type[0],
                    "body": notif_type[2].replace("${amount}", str(random.randint(1000, 2500))),
                    "is_read": random.random() > 0.5,
                    "action_url": f"/tenant/{notif_type[0]}/",
                },
            )

        self.stdout.write("  Created announcements, messages, and notifications")

    # =========================================================================
    # Documents
    # =========================================================================

    def _create_document_categories(self):
        from apps.documents.models import DocumentCategory

        self.stdout.write("Creating document categories...")

        categories = [
            ("Lease Agreements", "Signed lease documents and amendments"),
            ("Inspection Reports", "Move-in/move-out inspection reports"),
            ("Financial", "Payment receipts, invoices, and financial records"),
            ("Maintenance", "Work order documents and maintenance records"),
            ("Legal", "Legal notices, eviction documents, and court filings"),
            ("Insurance", "Insurance policies and claims"),
        ]
        for name, desc in categories:
            DocumentCategory.objects.get_or_create(name=name, defaults={"description": desc})

        self.stdout.write(f"  Created {len(categories)} document categories")

    def _create_document_folders_and_documents(self):
        from apps.documents.models import DocumentFolder, Document

        self.stdout.write("Creating document folders and documents...")

        folder_count = 0
        doc_count = 0

        for lease in self.leases:
            unit = lease.unit
            tenant = lease.tenant

            # Create folders
            folders = [
                ("Lease Documents", "Lease agreements and amendments", True),
                ("Receipts", "Payment receipts and invoices", True),
                ("Inspections", "Move-in/move-out inspection reports", True),
                ("Internal Notes", "Internal management notes", False),
            ]

            created_folders = {}
            for name, desc, visible in folders:
                folder, created = DocumentFolder.objects.get_or_create(
                    name=name,
                    unit=unit,
                    defaults={
                        "description": desc,
                        "lease": lease,
                        "is_tenant_visible": visible,
                        "created_by": self.admin_user,
                    },
                )
                created_folders[name] = folder
                if created:
                    folder_count += 1

            # Create documents
            doc, created = Document.objects.get_or_create(
                title=f"Lease Agreement - {tenant.get_full_name()}",
                unit=unit,
                document_type="lease",
                defaults={
                    "description": f"Signed lease agreement for {unit}",
                    "property": unit.property,
                    "lease": lease,
                    "tenant": tenant,
                    "folder": created_folders.get("Lease Documents"),
                    "is_tenant_visible": True,
                    "uploaded_by_role": "admin",
                    "file": "documents/sample/lease_agreement.pdf",
                    "file_size": 245000,
                    "mime_type": "application/pdf",
                    "created_by": self.admin_user,
                    "is_locked": True,
                },
            )
            if created:
                doc_count += 1

            doc, created = Document.objects.get_or_create(
                title=f"Move-in Inspection - {unit}",
                unit=unit,
                document_type="inspection",
                defaults={
                    "description": f"Move-in inspection report",
                    "property": unit.property,
                    "lease": lease,
                    "tenant": tenant,
                    "folder": created_folders.get("Inspections"),
                    "is_tenant_visible": True,
                    "uploaded_by_role": "admin",
                    "file": "documents/sample/inspection.pdf",
                    "file_size": 180000,
                    "mime_type": "application/pdf",
                    "created_by": self.admin_user,
                },
            )
            if created:
                doc_count += 1

        self.stdout.write(f"  Created {folder_count} folders and {doc_count} documents")

    # =========================================================================
    # Summary
    # =========================================================================

    def _print_summary(self):
        from apps.accounts.models import User
        from apps.properties.models import Property, Unit
        from apps.leases.models import Lease
        from apps.billing.models import Invoice, Payment
        from apps.workorders.models import WorkOrder
        from apps.rewards.models import RewardBalance

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("  DATA SUMMARY"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"  Tenants:       {User.objects.filter(role='tenant').count()}")
        self.stdout.write(f"  Properties:    {Property.objects.count()}")
        self.stdout.write(f"  Units:         {Unit.objects.count()}")
        self.stdout.write(f"  Active Leases: {Lease.objects.filter(status='active').count()}")
        self.stdout.write(f"  Invoices:      {Invoice.objects.count()}")
        self.stdout.write(f"  Payments:      {Payment.objects.count()}")
        self.stdout.write(f"  Work Orders:   {WorkOrder.objects.count()}")
        self.stdout.write(f"  Reward Balances > $0: {RewardBalance.objects.filter(balance__gt=0).count()}")
        self.stdout.write("")

    def _print_accounts(self):
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("  TEST ACCOUNTS"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("  ADMIN PORTAL: /admin-portal/login/"))
        self.stdout.write(f"  {'Username':<15} {'Password':<15} {'Role':<10}")
        self.stdout.write(f"  {'-'*15} {'-'*15} {'-'*10}")
        self.stdout.write(f"  {'admin':<15} {'admin123':<15} {'Admin':<10}")
        self.stdout.write(f"  {'staff':<15} {'staff123':<15} {'Staff':<10}")
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("  TENANT PORTAL: /tenant/login/"))
        self.stdout.write(f"  {'Username':<20} {'Password':<12} {'Scenario':<20}")
        self.stdout.write(f"  {'-'*20} {'-'*12} {'-'*20}")

        for scenario in TENANT_SCENARIOS[:8]:
            self.stdout.write(f"  {scenario['username']:<20} {'tenant123':<12} {scenario['scenario']:<20}")

        self.stdout.write(f"  ... and {len(TENANT_SCENARIOS) - 8} more tenants")
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("  DJANGO ADMIN: /django-admin/"))
        self.stdout.write(f"  {'admin':<15} {'admin123':<15}")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
