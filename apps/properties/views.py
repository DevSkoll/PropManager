from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.decorators import admin_required

from .forms import PropertyForm, UnitForm
from .models import Property, Unit


@admin_required
def property_list(request):
    properties = Property.objects.all()
    status_filter = request.GET.get("status")
    if status_filter == "active":
        properties = properties.filter(is_active=True)
    elif status_filter == "inactive":
        properties = properties.filter(is_active=False)
    return render(request, "properties/admin_property_list.html", {"properties": properties, "status_filter": status_filter})


@admin_required
def property_create(request):
    form = PropertyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        prop = form.save(commit=False)
        prop.created_by = request.user
        prop.save()
        messages.success(request, f"Property '{prop.name}' created successfully.")
        return redirect("properties_admin:property_detail", pk=prop.pk)
    return render(request, "properties/admin_property_form.html", {"form": form, "title": "Create Property"})


@admin_required
def property_detail(request, pk):
    prop = get_object_or_404(Property, pk=pk)
    units = prop.units.all()
    return render(request, "properties/admin_property_detail.html", {"property": prop, "units": units})


@admin_required
def property_edit(request, pk):
    prop = get_object_or_404(Property, pk=pk)
    form = PropertyForm(request.POST or None, instance=prop)
    if request.method == "POST" and form.is_valid():
        prop = form.save(commit=False)
        prop.updated_by = request.user
        prop.save()
        messages.success(request, f"Property '{prop.name}' updated successfully.")
        return redirect("properties_admin:property_detail", pk=prop.pk)
    return render(request, "properties/admin_property_form.html", {"form": form, "title": "Edit Property", "property": prop})


@admin_required
def unit_create(request, property_pk):
    prop = get_object_or_404(Property, pk=property_pk)
    form = UnitForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        unit = form.save(commit=False)
        unit.property = prop
        unit.save()
        messages.success(request, f"Unit '{unit.unit_number}' added to {prop.name}.")
        return redirect("properties_admin:property_detail", pk=prop.pk)
    return render(request, "properties/admin_unit_form.html", {"form": form, "property": prop, "title": "Add Unit"})


@admin_required
def unit_edit(request, property_pk, pk):
    prop = get_object_or_404(Property, pk=property_pk)
    unit = get_object_or_404(Unit, pk=pk, property=prop)
    form = UnitForm(request.POST or None, instance=unit)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Unit '{unit.unit_number}' updated.")
        return redirect("properties_admin:property_detail", pk=prop.pk)
    return render(request, "properties/admin_unit_form.html", {"form": form, "property": prop, "unit": unit, "title": "Edit Unit"})


@admin_required
def unit_detail(request, property_pk, pk):
    prop = get_object_or_404(Property, pk=property_pk)
    unit = get_object_or_404(Unit, pk=pk, property=prop)
    return render(request, "properties/admin_unit_detail.html", {"property": prop, "unit": unit})
