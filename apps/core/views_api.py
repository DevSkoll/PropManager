"""
Core API views for PropManager.

Provides API endpoints for global search and other cross-app functionality.
"""

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse

from apps.accounts.models import User
from apps.billing.models import Invoice
from apps.documents.models import EDocument
from apps.leases.models import Lease
from apps.properties.models import Property, Unit
from apps.workorders.models import WorkOrder


@login_required
def global_search_api(request):
    """
    Global search API endpoint.

    Searches across multiple models and returns categorized results.

    Query parameters:
    - q: Search query (required, min 2 characters)
    - limit: Max results per category (default 5)

    Returns JSON with categorized results.
    """
    query = request.GET.get("q", "").strip()

    if len(query) < 2:
        return JsonResponse({"error": "Query too short", "categories": {}}, status=400)

    limit = min(int(request.GET.get("limit", 5)), 10)  # Cap at 10
    categories = {}

    # 1. Search Tenants
    tenant_results = _search_tenants(query, limit)
    if tenant_results["results"]:
        categories["tenants"] = tenant_results

    # 2. Search Properties
    property_results = _search_properties(query, limit)
    if property_results["results"]:
        categories["properties"] = property_results

    # 3. Search Units
    unit_results = _search_units(query, limit)
    if unit_results["results"]:
        categories["units"] = unit_results

    # 4. Search Leases
    lease_results = _search_leases(query, limit)
    if lease_results["results"]:
        categories["leases"] = lease_results

    # 5. Search eDocuments
    document_results = _search_documents(query, limit)
    if document_results["results"]:
        categories["documents"] = document_results

    # 6. Search Work Orders
    workorder_results = _search_workorders(query, limit)
    if workorder_results["results"]:
        categories["work_orders"] = workorder_results

    # 7. Search Invoices
    invoice_results = _search_invoices(query, limit)
    if invoice_results["results"]:
        categories["invoices"] = invoice_results

    total_results = sum(cat.get("total", 0) for cat in categories.values())

    return JsonResponse({
        "query": query,
        "categories": categories,
        "total_results": total_results,
    })


def _search_tenants(query, limit):
    """Search tenant users by name, email, or phone."""
    queryset = User.objects.filter(
        Q(first_name__icontains=query)
        | Q(last_name__icontains=query)
        | Q(email__icontains=query)
        | Q(phone_number__icontains=query),
        role="tenant",
    )

    total = queryset.count()
    results = []

    for tenant in queryset[:limit]:
        results.append({
            "id": str(tenant.id),
            "title": tenant.get_full_name() or tenant.username,
            "subtitle": tenant.email,
            "url": f"{reverse('accounts_admin:admin_tenant_list')}?q={tenant.email}",
            "icon": "bi-person",
        })

    return {
        "label": "Tenants",
        "icon": "bi-people",
        "results": results,
        "total": total,
    }


def _search_properties(query, limit):
    """Search properties by name, address, or city."""
    queryset = Property.objects.filter(
        Q(name__icontains=query)
        | Q(address_line1__icontains=query)
        | Q(city__icontains=query),
        is_active=True,
    )

    total = queryset.count()
    results = []

    for prop in queryset[:limit]:
        results.append({
            "id": str(prop.id),
            "title": prop.name,
            "subtitle": f"{prop.city}, {prop.state}",
            "url": reverse("properties_admin:property_detail", kwargs={"pk": prop.pk}),
            "icon": "bi-building",
        })

    return {
        "label": "Properties",
        "icon": "bi-building",
        "results": results,
        "total": total,
    }


def _search_units(query, limit):
    """Search units by unit number or property name."""
    queryset = Unit.objects.filter(
        Q(unit_number__icontains=query) | Q(property__name__icontains=query)
    ).select_related("property")

    total = queryset.count()
    results = []

    for unit in queryset[:limit]:
        results.append({
            "id": str(unit.id),
            "title": f"Unit {unit.unit_number}",
            "subtitle": unit.property.name,
            "url": reverse(
                "properties_admin:unit_detail",
                kwargs={"property_pk": unit.property.pk, "pk": unit.pk},
            ),
            "icon": "bi-door-open",
        })

    return {
        "label": "Units",
        "icon": "bi-door-open",
        "results": results,
        "total": total,
    }


def _search_leases(query, limit):
    """Search leases by tenant name or unit number."""
    queryset = Lease.objects.filter(
        Q(tenant__first_name__icontains=query)
        | Q(tenant__last_name__icontains=query)
        | Q(unit__unit_number__icontains=query)
        | Q(unit__property__name__icontains=query)
    ).select_related("tenant", "unit", "unit__property")

    total = queryset.count()
    results = []

    for lease in queryset[:limit]:
        tenant_name = lease.tenant.get_full_name() or lease.tenant.username
        results.append({
            "id": str(lease.id),
            "title": f"{tenant_name} - Unit {lease.unit.unit_number}",
            "subtitle": f"{lease.get_status_display()} | {lease.unit.property.name}",
            "url": reverse("leases_admin:lease_detail", kwargs={"pk": lease.pk}),
            "icon": "bi-file-earmark-text",
        })

    return {
        "label": "Leases",
        "icon": "bi-file-earmark-text",
        "results": results,
        "total": total,
    }


def _search_documents(query, limit):
    """Search eDocuments by title or template name."""
    queryset = EDocument.objects.filter(
        Q(title__icontains=query) | Q(template__name__icontains=query)
    ).select_related("template")

    total = queryset.count()
    results = []

    for doc in queryset[:limit]:
        results.append({
            "id": str(doc.id),
            "title": doc.title,
            "subtitle": doc.get_status_display(),
            "url": reverse("documents_admin:edoc_detail", kwargs={"pk": doc.pk}),
            "icon": "bi-file-earmark-pdf",
        })

    return {
        "label": "Documents",
        "icon": "bi-file-earmark-pdf",
        "results": results,
        "total": total,
    }


def _search_workorders(query, limit):
    """Search work orders by title or description."""
    queryset = WorkOrder.objects.filter(
        Q(title__icontains=query) | Q(description__icontains=query)
    ).select_related("unit", "unit__property")

    total = queryset.count()
    results = []

    for wo in queryset[:limit]:
        results.append({
            "id": str(wo.id),
            "title": wo.title,
            "subtitle": f"{wo.get_status_display()} | {wo.unit.property.name}",
            "url": reverse("workorders_admin:workorder_detail", kwargs={"pk": wo.pk}),
            "icon": "bi-tools",
        })

    return {
        "label": "Work Orders",
        "icon": "bi-tools",
        "results": results,
        "total": total,
    }


def _search_invoices(query, limit):
    """Search invoices by invoice number or tenant name."""
    queryset = Invoice.objects.filter(
        Q(invoice_number__icontains=query)
        | Q(tenant__first_name__icontains=query)
        | Q(tenant__last_name__icontains=query)
    ).select_related("tenant")

    total = queryset.count()
    results = []

    for invoice in queryset[:limit]:
        tenant_name = invoice.tenant.get_full_name() or invoice.tenant.username
        results.append({
            "id": str(invoice.id),
            "title": f"Invoice {invoice.invoice_number}",
            "subtitle": f"{tenant_name} | {invoice.get_status_display()}",
            "url": reverse("billing_admin:invoice_detail", kwargs={"pk": invoice.pk}),
            "icon": "bi-receipt",
        })

    return {
        "label": "Invoices",
        "icon": "bi-receipt",
        "results": results,
        "total": total,
    }
