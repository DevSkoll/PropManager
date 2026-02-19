from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.decorators import admin_required, tenant_required

from .forms import LeaseForm, LeaseTermForm
from .models import Lease, LeaseTerm


@admin_required
def admin_lease_list(request):
    leases = Lease.objects.select_related("unit", "unit__property", "tenant").all()
    status_filter = request.GET.get("status")
    if status_filter:
        leases = leases.filter(status=status_filter)
    return render(request, "leases/admin_lease_list.html", {
        "leases": leases,
        "status_filter": status_filter,
        "status_choices": Lease.STATUS_CHOICES,
    })


@admin_required
def admin_lease_create(request):
    form = LeaseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        lease = form.save(commit=False)
        lease.created_by = request.user
        lease.save()
        messages.success(request, "Lease created successfully.")
        return redirect("leases_admin:lease_detail", pk=lease.pk)
    return render(request, "leases/admin_lease_form.html", {"form": form, "title": "Create Lease"})


@admin_required
def admin_lease_detail(request, pk):
    lease = get_object_or_404(Lease.objects.select_related("unit", "unit__property", "tenant"), pk=pk)
    terms = lease.terms.all()
    return render(request, "leases/admin_lease_detail.html", {"lease": lease, "terms": terms})


@admin_required
def admin_lease_edit(request, pk):
    lease = get_object_or_404(Lease, pk=pk)
    form = LeaseForm(request.POST or None, instance=lease)
    if request.method == "POST" and form.is_valid():
        lease = form.save(commit=False)
        lease.updated_by = request.user
        lease.save()
        messages.success(request, "Lease updated successfully.")
        return redirect("leases_admin:lease_detail", pk=lease.pk)
    return render(request, "leases/admin_lease_form.html", {"form": form, "title": "Edit Lease", "lease": lease})


@admin_required
def admin_lease_add_term(request, pk):
    lease = get_object_or_404(Lease, pk=pk)
    form = LeaseTermForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        term = form.save(commit=False)
        term.lease = lease
        term.save()
        messages.success(request, "Term added to lease.")
        return redirect("leases_admin:lease_detail", pk=lease.pk)
    return render(request, "leases/admin_lease_term_form.html", {"form": form, "lease": lease})


@tenant_required
def tenant_lease_detail(request):
    lease = Lease.objects.filter(
        tenant=request.user, status__in=["active", "renewed"]
    ).select_related("unit", "unit__property").first()
    terms = lease.terms.all() if lease else []
    return render(request, "leases/tenant_lease_detail.html", {"lease": lease, "terms": terms})
