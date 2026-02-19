"""
Management command to create default development accounts and sample data.

Usage:
    python manage.py seed_dev_data          # Create accounts + sample data
    python manage.py seed_dev_data --reset  # Wipe DB and recreate everything
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Seed the database with default development accounts and sample data"

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
        self._create_utility_configs()
        self._create_invoices()
        self._create_work_orders()
        self._create_communications()
        self._create_document_categories()
        self._create_document_folders_and_documents()

        self.stdout.write(self.style.SUCCESS("\nDevelopment data seeded successfully!"))
        self._print_accounts()

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

        # Tenant accounts
        tenant_data = [
            ("tenant1", "tenant1@example.com", "Jane", "Smith", "+15551234001"),
            ("tenant2", "tenant2@example.com", "Bob", "Johnson", "+15551234002"),
            ("tenant3", "tenant3@example.com", "Maria", "Garcia", "+15551234003"),
            ("tenant4", "tenant4@example.com", "David", "Williams", "+15551234004"),
            ("tenant5", "tenant5@example.com", "Sarah", "Brown", "+15551234005"),
        ]

        self.tenants = []
        for username, email, first, last, phone in tenant_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "first_name": first,
                    "last_name": last,
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
                    "emergency_contact_name": f"{first}'s Emergency Contact",
                    "emergency_contact_phone": phone.replace("1234", "5678"),
                    "move_in_date": date.today() - timedelta(days=random.randint(30, 365)),
                },
            )
            self.tenants.append(user)
            self.stdout.write(f"  {'Created' if created else 'Updated'}: {username} (Tenant)")

    def _create_properties(self):
        from apps.properties.models import Property, Unit, Amenity

        self.stdout.write("Creating properties and units...")

        # Properties
        props_data = [
            ("Sunset Apartments", "apartment", "100 Sunset Blvd", "Los Angeles", "CA", "90028", 8),
            ("Maple Grove Townhomes", "townhouse", "250 Maple Ave", "Portland", "OR", "97201", 4),
            ("Oak Street House", "single_family", "42 Oak Street", "Austin", "TX", "78701", 1),
        ]

        self.properties = []
        for name, ptype, addr, city, state, zipcode, num_units in props_data:
            prop, created = Property.objects.get_or_create(
                name=name,
                defaults={
                    "property_type": ptype,
                    "address_line1": addr,
                    "city": city,
                    "state": state,
                    "zip_code": zipcode,
                    "total_units": num_units,
                    "is_active": True,
                    "created_by": self.admin_user,
                },
            )
            self.properties.append(prop)
            self.stdout.write(f"  {'Created' if created else 'Exists'}: {name}")

        # Units for Sunset Apartments
        rents = [1200, 1350, 1500, 1650, 1800, 1200, 1350, 1500]
        self.units = []
        for i in range(1, 9):
            unit, _ = Unit.objects.get_or_create(
                property=self.properties[0],
                unit_number=f"{100 + i}",
                defaults={
                    "bedrooms": 1 if i <= 4 else 2,
                    "bathrooms": Decimal("1.0") if i <= 4 else Decimal("1.5"),
                    "square_feet": 650 if i <= 4 else 900,
                    "base_rent": Decimal(str(rents[i - 1])),
                    "status": "occupied" if i <= 5 else "vacant",
                    "floor": 1 if i <= 4 else 2,
                },
            )
            self.units.append(unit)

        # Units for Maple Grove
        for i in range(1, 5):
            unit, _ = Unit.objects.get_or_create(
                property=self.properties[1],
                unit_number=f"TH-{i}",
                defaults={
                    "bedrooms": 3,
                    "bathrooms": Decimal("2.5"),
                    "square_feet": 1400,
                    "base_rent": Decimal("2200"),
                    "status": "vacant",
                    "floor": 1,
                },
            )
            self.units.append(unit)

        # Unit for Oak Street
        unit, _ = Unit.objects.get_or_create(
            property=self.properties[2],
            unit_number="A",
            defaults={
                "bedrooms": 4,
                "bathrooms": Decimal("2.0"),
                "square_feet": 1800,
                "base_rent": Decimal("2500"),
                "status": "vacant",
            },
        )
        self.units.append(unit)

        # Amenities
        amenity_names = [
            "In-Unit Washer/Dryer", "Dishwasher", "Central AC",
            "Parking Spot", "Balcony", "Pet Friendly",
        ]
        for name in amenity_names:
            Amenity.objects.get_or_create(name=name)

        self.stdout.write(f"  Created {len(self.units)} units, {len(amenity_names)} amenities")

    def _create_leases(self):
        from apps.leases.models import Lease, LeaseTerm

        self.stdout.write("Creating leases...")

        self.leases = []
        # Assign first 5 tenants to first 5 units of Sunset Apartments
        for i, tenant in enumerate(self.tenants):
            unit = self.units[i]
            lease, created = Lease.objects.get_or_create(
                unit=unit,
                tenant=tenant,
                status="active",
                defaults={
                    "lease_type": "fixed",
                    "start_date": date.today() - timedelta(days=random.randint(60, 300)),
                    "end_date": date.today() + timedelta(days=random.randint(60, 300)),
                    "monthly_rent": unit.base_rent,
                    "security_deposit": unit.base_rent,
                    "created_by": self.admin_user,
                },
            )
            # Mark the unit as occupied
            unit.status = "occupied"
            unit.save()
            self.leases.append(lease)

            if created:
                # Add standard terms
                LeaseTerm.objects.get_or_create(
                    lease=lease,
                    title="Quiet Hours",
                    defaults={
                        "description": "Quiet hours are from 10:00 PM to 8:00 AM.",
                        "is_standard": True,
                    },
                )
                LeaseTerm.objects.get_or_create(
                    lease=lease,
                    title="Pet Policy",
                    defaults={
                        "description": "Small pets allowed with a $300 refundable pet deposit.",
                        "is_standard": True,
                    },
                )

            self.stdout.write(f"  {'Created' if created else 'Exists'}: {tenant.get_full_name()} @ {unit}")

    def _create_utility_configs(self):
        from apps.billing.models import UtilityConfig

        self.stdout.write("Creating utility configurations...")

        # Configure utilities for the first 5 units (occupied ones in Sunset Apartments)
        configs = [
            # (unit_index, utility_type, billing_mode, rate)
            # Unit 101 - Jane Smith
            (0, "water", "fixed", Decimal("45.00")),
            (0, "electric", "variable", Decimal("87.50")),
            (0, "gas", "included", Decimal("0.00")),
            (0, "trash", "fixed", Decimal("25.00")),
            (0, "parking", "fixed", Decimal("75.00")),
            (0, "pet_fee", "tenant_pays", Decimal("0.00")),
            # Unit 102 - Bob Johnson
            (1, "water", "fixed", Decimal("45.00")),
            (1, "electric", "variable", Decimal("92.00")),
            (1, "gas", "included", Decimal("0.00")),
            (1, "trash", "fixed", Decimal("25.00")),
            (1, "parking", "tenant_pays", Decimal("0.00")),
            (1, "pet_fee", "fixed", Decimal("35.00")),
            # Unit 103 - Maria Garcia
            (2, "water", "fixed", Decimal("45.00")),
            (2, "electric", "fixed", Decimal("110.00")),
            (2, "gas", "fixed", Decimal("40.00")),
            (2, "trash", "included", Decimal("0.00")),
            # Unit 104 - David Williams
            (3, "water", "included", Decimal("0.00")),
            (3, "electric", "variable", Decimal("78.25")),
            (3, "gas", "included", Decimal("0.00")),
            (3, "trash", "fixed", Decimal("25.00")),
            # Unit 105 - Sarah Brown
            (4, "water", "fixed", Decimal("50.00")),
            (4, "electric", "variable", Decimal("95.00")),
            (4, "gas", "tenant_pays", Decimal("0.00")),
            (4, "trash", "fixed", Decimal("25.00")),
            (4, "parking", "fixed", Decimal("75.00")),
        ]

        created_count = 0
        for unit_idx, utype, mode, rate in configs:
            _, created = UtilityConfig.objects.get_or_create(
                unit=self.units[unit_idx],
                utility_type=utype,
                defaults={
                    "billing_mode": mode,
                    "rate": rate,
                    "is_active": True,
                },
            )
            if created:
                created_count += 1

        self.stdout.write(f"  Created {created_count} utility configurations across 5 units")

    def _create_invoices(self):
        from apps.billing.models import Invoice, InvoiceLineItem, Payment

        self.stdout.write("Creating invoices and payments...")

        today = date.today()

        for i, lease in enumerate(self.leases):
            # Current month invoice - issued
            inv_num = f"INV-{today.strftime('%Y%m')}-{1001 + i}"
            invoice, created = Invoice.objects.get_or_create(
                invoice_number=inv_num,
                defaults={
                    "lease": lease,
                    "tenant": lease.tenant,
                    "status": "issued",
                    "issue_date": today.replace(day=1),
                    "due_date": today.replace(day=5),
                    "total_amount": lease.monthly_rent,
                    "amount_paid": Decimal("0"),
                    "created_by": self.admin_user,
                },
            )
            if created:
                InvoiceLineItem.objects.create(
                    invoice=invoice,
                    charge_type="rent",
                    description=f"Monthly Rent - {today.strftime('%B %Y')}",
                    quantity=1,
                    unit_price=lease.monthly_rent,
                    amount=lease.monthly_rent,
                )

            # Last month invoice - paid
            last_month = (today.replace(day=1) - timedelta(days=1))
            inv_num_prev = f"INV-{last_month.strftime('%Y%m')}-{1001 + i}"
            prev_invoice, created = Invoice.objects.get_or_create(
                invoice_number=inv_num_prev,
                defaults={
                    "lease": lease,
                    "tenant": lease.tenant,
                    "status": "paid",
                    "issue_date": last_month.replace(day=1),
                    "due_date": last_month.replace(day=5),
                    "total_amount": lease.monthly_rent,
                    "amount_paid": lease.monthly_rent,
                    "created_by": self.admin_user,
                },
            )
            if created:
                InvoiceLineItem.objects.create(
                    invoice=prev_invoice,
                    charge_type="rent",
                    description=f"Monthly Rent - {last_month.strftime('%B %Y')}",
                    quantity=1,
                    unit_price=lease.monthly_rent,
                    amount=lease.monthly_rent,
                )
                Payment.objects.create(
                    tenant=lease.tenant,
                    invoice=prev_invoice,
                    amount=lease.monthly_rent,
                    method="online",
                    status="completed",
                    reference_number=f"PAY-{random.randint(100000, 999999)}",
                )

        # Make one tenant overdue
        overdue_inv = Invoice.objects.filter(
            tenant=self.tenants[2],
            status="issued",
        ).first()
        if overdue_inv:
            overdue_inv.status = "overdue"
            overdue_inv.due_date = today - timedelta(days=15)
            overdue_inv.save()

        self.stdout.write(f"  Created invoices for {len(self.leases)} tenants (2 months each)")

    def _create_work_orders(self):
        from apps.workorders.models import WorkOrder, WorkOrderNote

        self.stdout.write("Creating work orders...")

        wo_data = [
            (self.tenants[0], self.units[0], "Leaking kitchen faucet", "The kitchen faucet has been dripping constantly for the past 2 days.", "plumbing", "high", "verified"),
            (self.tenants[1], self.units[1], "AC not cooling properly", "The apartment stays at 80F even with AC on full blast.", "hvac", "high", "assigned"),
            (self.tenants[2], self.units[2], "Light fixture flickering", "The living room ceiling light flickers on and off randomly.", "electrical", "medium", "created"),
            (self.tenants[3], self.units[3], "Dishwasher not draining", "Water remains at the bottom of the dishwasher after cycles.", "appliance", "medium", "in_progress"),
            (self.tenants[0], self.units[0], "Front door lock sticking", "The front door lock is very difficult to turn.", "general", "low", "completed"),
        ]

        for tenant, unit, title, desc, category, priority, status in wo_data:
            wo, created = WorkOrder.objects.get_or_create(
                title=title,
                unit=unit,
                defaults={
                    "description": desc,
                    "reported_by": tenant,
                    "status": status,
                    "priority": priority,
                    "category": category,
                    "scheduled_date": date.today() + timedelta(days=random.randint(1, 14)),
                    "cost_estimate": Decimal(str(random.randint(50, 500))),
                    "created_by": tenant,
                },
            )
            if created and status in ("completed",):
                wo.actual_cost = Decimal(str(random.randint(50, 300)))
                wo.completed_date = date.today() - timedelta(days=random.randint(1, 7))
                wo.save()

                WorkOrderNote.objects.create(
                    work_order=wo,
                    author_user=self.admin_user,
                    text="Issue resolved. Lock mechanism replaced.",
                    is_internal=False,
                )

            self.stdout.write(f"  {'Created' if created else 'Exists'}: {title} [{status}]")

    def _create_communications(self):
        from apps.communications.models import Announcement, MessageThread, Message, Notification

        self.stdout.write("Creating communications...")

        # Announcements
        ann, created = Announcement.objects.get_or_create(
            title="Building Maintenance Notice",
            defaults={
                "body": "The water will be shut off on Friday March 7th from 9 AM to 12 PM for scheduled pipe maintenance. Please plan accordingly.",
                "author": self.admin_user,
                "property": self.properties[0],
                "is_published": True,
                "published_at": timezone.now() - timedelta(days=1),
            },
        )

        ann2, _ = Announcement.objects.get_or_create(
            title="Holiday Office Hours",
            defaults={
                "body": "The management office will be closed on Monday for the holiday. For emergencies, please call the maintenance hotline.",
                "author": self.admin_user,
                "is_published": True,
                "published_at": timezone.now() - timedelta(hours=12),
            },
        )

        # Message thread between tenant and admin
        thread, created = MessageThread.objects.get_or_create(
            subject="Question about parking",
        )
        if created:
            thread.participants.add(self.tenants[0], self.admin_user)
            Message.objects.create(
                thread=thread,
                sender=self.tenants[0],
                body="Hi, I wanted to ask about getting a second parking spot. Is that possible?",
            )
            Message.objects.create(
                thread=thread,
                sender=self.admin_user,
                body="Hi Jane! Yes, we have additional parking spots available for $75/month. Would you like me to add one to your lease?",
            )

        # Sample notifications
        for tenant in self.tenants[:3]:
            Notification.objects.get_or_create(
                recipient=tenant,
                title="Rent Due Reminder",
                defaults={
                    "channel": "in_app",
                    "category": "billing",
                    "body": "Your rent for this month is due in 5 days.",
                    "is_read": False,
                    "action_url": "/tenant/billing/",
                },
            )

        self.stdout.write("  Created announcements, messages, and notifications")

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

        self.stdout.write("Creating document folders and sample documents...")

        folder_count = 0
        doc_count = 0
        for i, lease in enumerate(self.leases):
            unit = lease.unit
            tenant = lease.tenant

            # Create folders per unit
            lease_folder, created = DocumentFolder.objects.get_or_create(
                name="Lease Documents",
                unit=unit,
                defaults={
                    "description": "Lease agreements and amendments",
                    "lease": lease,
                    "is_tenant_visible": True,
                    "created_by": self.admin_user,
                },
            )
            if created:
                folder_count += 1

            receipts_folder, created = DocumentFolder.objects.get_or_create(
                name="Receipts",
                unit=unit,
                defaults={
                    "description": "Payment receipts and invoices",
                    "lease": lease,
                    "is_tenant_visible": True,
                    "created_by": self.admin_user,
                },
            )
            if created:
                folder_count += 1

            inspections_folder, created = DocumentFolder.objects.get_or_create(
                name="Inspections",
                unit=unit,
                defaults={
                    "description": "Move-in/move-out inspection reports",
                    "lease": lease,
                    "is_tenant_visible": True,
                    "created_by": self.admin_user,
                },
            )
            if created:
                folder_count += 1

            # Admin-only folder
            internal_folder, created = DocumentFolder.objects.get_or_create(
                name="Internal Notes",
                unit=unit,
                defaults={
                    "description": "Internal management notes (not visible to tenants)",
                    "is_tenant_visible": False,
                    "created_by": self.admin_user,
                },
            )
            if created:
                folder_count += 1

            # Sample admin-uploaded documents (no actual files in dev seed)
            doc, created = Document.objects.get_or_create(
                title=f"Lease Agreement - {tenant.get_full_name()}",
                unit=unit,
                document_type="lease",
                defaults={
                    "description": f"Signed lease agreement for {unit}",
                    "property": unit.property,
                    "lease": lease,
                    "tenant": tenant,
                    "folder": lease_folder,
                    "is_tenant_visible": True,
                    "uploaded_by_role": "admin",
                    "file": "documents/sample/lease_agreement.pdf",
                    "file_size": 245000,
                    "mime_type": "application/pdf",
                    "created_by": self.admin_user,
                },
            )
            if created:
                doc_count += 1

            doc, created = Document.objects.get_or_create(
                title=f"Move-in Inspection - {unit}",
                unit=unit,
                document_type="inspection",
                defaults={
                    "description": f"Move-in inspection report for {unit}",
                    "property": unit.property,
                    "lease": lease,
                    "tenant": tenant,
                    "folder": inspections_folder,
                    "is_tenant_visible": True,
                    "uploaded_by_role": "admin",
                    "file": "documents/sample/inspection_report.pdf",
                    "file_size": 180000,
                    "mime_type": "application/pdf",
                    "created_by": self.admin_user,
                },
            )
            if created:
                doc_count += 1

            # Lock the first tenant's lease doc
            if i == 0:
                locked_doc = Document.objects.filter(
                    title=f"Lease Agreement - {tenant.get_full_name()}"
                ).first()
                if locked_doc and not locked_doc.is_locked:
                    locked_doc.lock(self.admin_user)

            # Sample tenant-uploaded document (first 2 tenants)
            if i < 2:
                doc, created = Document.objects.get_or_create(
                    title=f"Rent Receipt - {tenant.get_full_name()}",
                    created_by=tenant,
                    uploaded_by_role="tenant",
                    defaults={
                        "document_type": "receipt",
                        "description": "Payment receipt for last month's rent",
                        "unit": unit,
                        "lease": lease,
                        "tenant": tenant,
                        "folder": receipts_folder,
                        "is_tenant_visible": True,
                        "file": "documents/sample/receipt.pdf",
                        "file_size": 52000,
                        "mime_type": "application/pdf",
                    },
                )
                if created:
                    doc_count += 1

        self.stdout.write(f"  Created {folder_count} folders and {doc_count} documents")

    def _print_accounts(self):
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("  DEFAULT DEVELOPMENT ACCOUNTS"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("  ADMIN PORTAL: /admin-portal/login/"))
        self.stdout.write(f"  {'Username':<15} {'Password':<15} {'Role':<10}")
        self.stdout.write(f"  {'-'*15} {'-'*15} {'-'*10}")
        self.stdout.write(f"  {'admin':<15} {'admin123':<15} {'Admin':<10}")
        self.stdout.write(f"  {'staff':<15} {'staff123':<15} {'Staff':<10}")
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("  TENANT PORTAL: /tenant/login/"))
        self.stdout.write(f"  {'Username/Email':<30} {'Password':<15} {'Name':<20}")
        self.stdout.write(f"  {'-'*30} {'-'*15} {'-'*20}")
        self.stdout.write(f"  {'tenant1@example.com':<30} {'tenant123':<15} {'Jane Smith':<20}")
        self.stdout.write(f"  {'tenant2@example.com':<30} {'tenant123':<15} {'Bob Johnson':<20}")
        self.stdout.write(f"  {'tenant3@example.com':<30} {'tenant123':<15} {'Maria Garcia':<20}")
        self.stdout.write(f"  {'tenant4@example.com':<30} {'tenant123':<15} {'David Williams':<20}")
        self.stdout.write(f"  {'tenant5@example.com':<30} {'tenant123':<15} {'Sarah Brown':<20}")
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("  DJANGO ADMIN: /django-admin/"))
        self.stdout.write(f"  {'admin':<15} {'admin123':<15}")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
