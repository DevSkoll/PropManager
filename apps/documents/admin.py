from django.contrib import admin

from .models import Document, DocumentCategory


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "document_type", "category", "is_tenant_visible", "created_at")
    list_filter = ("document_type", "is_tenant_visible", "category")
    search_fields = ("title", "description")
