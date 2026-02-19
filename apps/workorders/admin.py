from django.contrib import admin

from .models import ContractorAssignment, WorkOrder, WorkOrderImage, WorkOrderNote


class WorkOrderNoteInline(admin.TabularInline):
    model = WorkOrderNote
    extra = 0


class WorkOrderImageInline(admin.TabularInline):
    model = WorkOrderImage
    extra = 0


class ContractorAssignmentInline(admin.TabularInline):
    model = ContractorAssignment
    extra = 0


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ("title", "unit", "status", "priority", "category", "reported_by", "created_at")
    list_filter = ("status", "priority", "category")
    search_fields = ("title", "description", "unit__unit_number", "unit__property__name")
    inlines = [ContractorAssignmentInline, WorkOrderNoteInline, WorkOrderImageInline]
