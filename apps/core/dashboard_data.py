"""
Dashboard app launcher configuration and badge calculations.

Defines all app tiles, categories, and badge notification logic
for the modern admin dashboard launcher.
"""

from django.urls import reverse


class AppTile:
    """Represents a single app tile in the launcher."""

    def __init__(
        self,
        id,
        name,
        description,
        icon,
        url,
        category,
        gradient,
        badge_func=None,
        favorite=False,
        keywords=None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.icon = icon  # Bootstrap icon class
        self.url = url
        self.category = category
        self.gradient = gradient
        self.badge_func = badge_func
        self.favorite = favorite
        self.keywords = keywords or []

    def get_badge_count(self, request):
        """Calculate badge count for this app."""
        if self.badge_func:
            return self.badge_func(request)
        return 0


def get_app_tiles():
    """Return all app tile definitions."""

    return [
        # ===== Dashboard & Analytics =====
        AppTile(
            id="dashboard",
            name="Dashboard",
            description="Overview & quick stats",
            icon="bi-speedometer2",
            url="accounts_admin:admin_dashboard",
            category="dashboard",
            gradient="purple",
            keywords=["home", "overview", "main"],
        ),
        AppTile(
            id="analytics",
            name="Analytics",
            description="Charts & trends",
            icon="bi-graph-up-arrow",
            url="accounts_admin:admin_analytics_dashboard",
            category="dashboard",
            gradient="purple",
            keywords=["reports", "metrics", "charts", "data"],
        ),
        # ===== Properties & Units =====
        AppTile(
            id="properties",
            name="Properties",
            description="Manage properties",
            icon="bi-building",
            url="properties_admin:property_list",
            category="properties",
            gradient="blue",
            keywords=["buildings", "locations", "real estate"],
        ),
        AppTile(
            id="units",
            name="Units",
            description="Manage rental units",
            icon="bi-door-closed",
            url="properties_admin:property_list",  # Units accessed via properties
            category="properties",
            gradient="blue",
            keywords=["apartments", "rentals", "spaces"],
        ),
        # ===== Leases & Tenants =====
        AppTile(
            id="leases",
            name="Leases",
            description="Lease agreements",
            icon="bi-file-earmark-text",
            url="leases_admin:lease_list",
            category="leases",
            gradient="teal",
            badge_func=lambda req: _get_pending_signatures(),
            keywords=["contracts", "agreements", "terms"],
        ),
        AppTile(
            id="tenants",
            name="Tenants",
            description="Tenant management",
            icon="bi-people",
            url="accounts_admin:admin_tenant_list",
            category="leases",
            gradient="teal",
            keywords=["residents", "occupants", "renters"],
        ),
        AppTile(
            id="send_signature",
            name="Send for Signature",
            description="eSignature workflow",
            icon="bi-pen",
            url="leases_admin:lease_list",
            category="leases",
            gradient="teal",
            keywords=["sign", "esign", "signature", "execute"],
        ),
        AppTile(
            id="onboarding",
            name="Tenant Onboarding",
            description="Move-in process",
            icon="bi-person-plus",
            url="tenant_lifecycle_admin:admin_session_list",
            category="leases",
            gradient="teal",
            badge_func=lambda req: _get_active_onboarding_sessions(),
            keywords=["onboard", "move-in", "new tenant", "invite"],
        ),
        AppTile(
            id="onboarding_templates",
            name="Onboarding Templates",
            description="Configure onboarding",
            icon="bi-clipboard-check",
            url="tenant_lifecycle_admin:admin_template_list",
            category="leases",
            gradient="teal",
            keywords=["templates", "configuration", "setup"],
        ),
        # ===== Billing & Payments =====
        AppTile(
            id="invoices",
            name="Invoices",
            description="Billing & invoices",
            icon="bi-receipt",
            url="billing_admin:invoice_list",
            category="billing",
            gradient="green",
            badge_func=lambda req: _get_overdue_invoices(),
            keywords=["bills", "charges", "statements"],
        ),
        AppTile(
            id="payments",
            name="Payments",
            description="Payment history",
            icon="bi-cash-stack",
            url="billing_admin:payment_list",
            category="billing",
            gradient="green",
            keywords=["transactions", "revenue", "collections"],
        ),
        AppTile(
            id="gateways",
            name="Payment Gateways",
            description="Gateway configuration",
            icon="bi-credit-card",
            url="billing_admin:gateway_settings",
            category="billing",
            gradient="green",
            keywords=["stripe", "square", "authorize", "processors"],
        ),
        AppTile(
            id="bitcoin",
            name="Bitcoin Wallet",
            description="Crypto payments",
            icon="bi-currency-bitcoin",
            url="billing_admin:bitcoin_dashboard",
            category="billing",
            gradient="green",
            keywords=["crypto", "btc", "cryptocurrency", "blockchain"],
        ),
        AppTile(
            id="recurring",
            name="Recurring Charges",
            description="Auto-billing setup",
            icon="bi-arrow-repeat",
            url="billing_admin:invoice_list",  # Accessible via invoice management
            category="billing",
            gradient="green",
            keywords=["auto", "subscription", "recurring"],
        ),
        AppTile(
            id="utilities",
            name="Utilities",
            description="Utility billing config",
            icon="bi-lightning-charge",
            url="billing_admin:utility_bulk_set",
            category="billing",
            gradient="green",
            keywords=["water", "electric", "gas", "sewer"],
        ),
        AppTile(
            id="late_fees",
            name="Late Fees",
            description="Apply late charges",
            icon="bi-exclamation-triangle",
            url="billing_admin:invoice_list",  # Late fees applied via invoice list
            category="billing",
            gradient="green",
            keywords=["penalties", "charges", "overdue"],
        ),
        # ===== Maintenance =====
        AppTile(
            id="workorders",
            name="Work Orders",
            description="Maintenance requests",
            icon="bi-tools",
            url="workorders_admin:workorder_list",
            category="maintenance",
            gradient="orange",
            badge_func=lambda req: _get_emergency_workorders(),
            keywords=["maintenance", "repairs", "tickets", "service"],
        ),
        # ===== Tenant Programs =====
        AppTile(
            id="rewards_config",
            name="Rewards Config",
            description="Property reward settings",
            icon="bi-gear",
            url="rewards_admin:property_rewards_list",
            category="tenant_programs",
            gradient="pink",
            keywords=["settings", "loyalty", "configuration"],
        ),
        AppTile(
            id="grant_rewards",
            name="Grant Rewards",
            description="Issue reward points",
            icon="bi-gift",
            url="rewards_admin:grant_reward",
            category="tenant_programs",
            gradient="pink",
            keywords=["give", "award", "bonus", "points"],
        ),
        AppTile(
            id="reward_balances",
            name="Reward Balances",
            description="Tenant balances",
            icon="bi-wallet2",
            url="rewards_admin:reward_balances",
            category="tenant_programs",
            gradient="pink",
            keywords=["points", "credits", "balance"],
        ),
        # ===== Communications =====
        AppTile(
            id="messages",
            name="Messages",
            description="Tenant communications",
            icon="bi-chat-dots",
            url="communications_admin:thread_list",
            category="communications",
            gradient="indigo",
            keywords=["inbox", "chat", "conversations"],
        ),
        AppTile(
            id="announcements",
            name="Announcements",
            description="Broadcast messages",
            icon="bi-megaphone",
            url="communications_admin:announcement_list",
            category="communications",
            gradient="indigo",
            keywords=["broadcast", "notify", "alerts"],
        ),
        AppTile(
            id="notification_groups",
            name="Notification Groups",
            description="Manage groups",
            icon="bi-bell",
            url="notifications_admin:group_list",
            category="communications",
            gradient="indigo",
            keywords=["alerts", "subscribers", "lists"],
        ),
        AppTile(
            id="comm_settings",
            name="Email/SMS Config",
            description="Communication settings",
            icon="bi-envelope-at",
            url="notifications_admin:group_list",  # Settings accessible from notifications
            category="communications",
            gradient="indigo",
            keywords=["email", "sms", "text", "configuration"],
        ),
        # ===== Documents =====
        AppTile(
            id="documents",
            name="Documents",
            description="File management",
            icon="bi-folder",
            url="documents_admin:document_list",
            category="documents",
            gradient="cyan",
            keywords=["files", "storage", "uploads"],
        ),
        AppTile(
            id="folders",
            name="Folders",
            description="Organize files",
            icon="bi-folder2-open",
            url="documents_admin:folder_list",
            category="documents",
            gradient="cyan",
            keywords=["directories", "organize", "structure"],
        ),
        AppTile(
            id="edocuments",
            name="eDocuments",
            description="Digital signatures",
            icon="bi-pen",
            url="documents_admin:edoc_list",
            category="documents",
            gradient="cyan",
            keywords=["sign", "esign", "signature", "contracts"],
        ),
        AppTile(
            id="edoc_templates",
            name="eDoc Templates",
            description="Document templates",
            icon="bi-file-earmark-code",
            url="documents_admin:template_list",
            category="documents",
            gradient="cyan",
            keywords=["forms", "contracts", "templates"],
        ),
        # ===== Reports =====
        AppTile(
            id="reports",
            name="Reports",
            description="All reports",
            icon="bi-file-bar-graph",
            url="reports:index",
            category="reports",
            gradient="gray",
            keywords=["analytics", "export", "data"],
        ),
        AppTile(
            id="rent_roll",
            name="Rent Roll",
            description="Rent roll report",
            icon="bi-table",
            url="reports:rent_roll",
            category="reports",
            gradient="gray",
            keywords=["rent", "tenants", "occupancy"],
        ),
        AppTile(
            id="aging",
            name="Aging Receivables",
            description="Outstanding balances",
            icon="bi-clock-history",
            url="reports:aging_receivables",
            category="reports",
            gradient="gray",
            keywords=["overdue", "collections", "ar"],
        ),
        AppTile(
            id="payment_history",
            name="Payment History",
            description="Payment report",
            icon="bi-cash",
            url="reports:payment_history",
            category="reports",
            gradient="gray",
            keywords=["transactions", "revenue", "history"],
        ),
        AppTile(
            id="wo_reports",
            name="Work Order Reports",
            description="Maintenance analytics",
            icon="bi-bar-chart",
            url="reports:index",
            category="reports",
            gradient="gray",
            keywords=["maintenance", "analytics", "metrics"],
        ),
        # ===== Operations =====
        AppTile(
            id="weather",
            name="Weather",
            description="Weather monitoring",
            icon="bi-cloud-sun",
            url="weather_admin:weather_dashboard",
            category="operations",
            gradient="red",
            keywords=["alerts", "forecast", "climate"],
        ),
        AppTile(
            id="marketing",
            name="Marketing",
            description="Campaign management",
            icon="bi-bullseye",
            url="marketing_admin:campaign_list",
            category="operations",
            gradient="red",
            keywords=["campaigns", "leads", "email"],
        ),
        AppTile(
            id="settings",
            name="Settings",
            description="Admin settings",
            icon="bi-gear-wide",
            url="accounts_admin:admin_settings",
            category="operations",
            gradient="red",
            keywords=["config", "preferences", "profile"],
        ),
        # ===== AI & Automation =====
        AppTile(
            id="ai_gateway",
            name="AI Gateway",
            description="Manage AI providers",
            icon="bi-robot",
            url="ai_admin:dashboard",
            category="ai",
            gradient="purple",
            keywords=["ai", "llm", "openai", "anthropic", "claude", "gpt"],
        ),
        AppTile(
            id="ai_providers",
            name="Add AI Provider",
            description="Configure new AI",
            icon="bi-plus-circle",
            url="ai_admin:provider_create",
            category="ai",
            gradient="purple",
            keywords=["add", "new", "provider", "configure"],
        ),
    ]


# ===== Badge Calculation Helpers =====


def _get_overdue_invoices():
    """Get count of overdue invoices."""
    try:
        from apps.billing.models import Invoice

        return Invoice.objects.filter(status="overdue").count()
    except Exception:
        return 0


def _get_pending_signatures():
    """Get count of leases with pending signatures."""
    try:
        from apps.documents.models import EDocument

        return EDocument.objects.filter(status__in=["pending", "partial"]).count()
    except Exception:
        return 0


def _get_emergency_workorders():
    """Get count of emergency work orders that are still open."""
    try:
        from apps.workorders.models import WorkOrder

        return (
            WorkOrder.objects.filter(priority="emergency")
            .exclude(status__in=["completed", "closed"])
            .count()
        )
    except Exception:
        return 0


def _get_active_onboarding_sessions():
    """Get count of active onboarding sessions (in progress)."""
    try:
        from apps.tenant_lifecycle.models import OnboardingSession

        return OnboardingSession.objects.filter(
            status__in=["invited", "started", "in_progress"]
        ).count()
    except Exception:
        return 0


# ===== Category Information =====

CATEGORY_INFO = {
    "dashboard": {"name": "Dashboard & Analytics", "icon": "bi-speedometer2", "order": 1},
    "properties": {"name": "Properties & Units", "icon": "bi-building", "order": 2},
    "leases": {"name": "Leases & Tenants", "icon": "bi-file-earmark-text", "order": 3},
    "billing": {"name": "Billing & Payments", "icon": "bi-currency-dollar", "order": 4},
    "maintenance": {"name": "Maintenance", "icon": "bi-tools", "order": 5},
    "tenant_programs": {"name": "Tenant Programs", "icon": "bi-gift", "order": 6},
    "communications": {"name": "Communications", "icon": "bi-megaphone", "order": 7},
    "documents": {"name": "Documents", "icon": "bi-folder", "order": 8},
    "reports": {"name": "Reports", "icon": "bi-file-bar-graph", "order": 9},
    "operations": {"name": "Operations", "icon": "bi-sliders", "order": 10},
    "ai": {"name": "AI & Automation", "icon": "bi-robot", "order": 11},
}
