from django.contrib import admin

from .models import Document, DocumentCategory, DocumentFolder


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(DocumentFolder)
class DocumentFolderAdmin(admin.ModelAdmin):
    list_display = ("name", "unit", "lease", "is_tenant_visible", "created_at")
    list_filter = ("is_tenant_visible",)
    search_fields = ("name", "description")
    raw_id_fields = ("unit", "lease")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title", "document_type", "category", "uploaded_by_role",
        "is_tenant_visible", "is_locked", "deleted_at", "created_at",
    )
    list_filter = ("document_type", "is_tenant_visible", "uploaded_by_role", "is_locked", "category")
    search_fields = ("title", "description")
    raw_id_fields = ("folder", "tenant", "deleted_by", "locked_by")

    def get_queryset(self, request):
        return Document.all_objects.all()
