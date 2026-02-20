from django.contrib import admin

from .models import (
    Document,
    DocumentCategory,
    DocumentFolder,
    EDocument,
    EDocumentSignatureBlock,
    EDocumentSigner,
    EDocumentTemplate,
)


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


# =============================================================================
# eDocument Admin Classes
# =============================================================================


@admin.register(EDocumentTemplate)
class EDocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "template_type", "property", "is_active", "created_at")
    list_filter = ("template_type", "is_active")
    search_fields = ("name", "description", "content")
    raw_id_fields = ("property",)
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")

    fieldsets = (
        (None, {
            "fields": ("name", "template_type", "description", "is_active", "property")
        }),
        ("Content", {
            "fields": ("content",),
            "classes": ("wide",),
        }),
        ("Audit", {
            "fields": ("created_at", "updated_at", "created_by", "updated_by"),
            "classes": ("collapse",),
        }),
    )


class EDocumentSignerInline(admin.TabularInline):
    model = EDocumentSigner
    extra = 0
    readonly_fields = ("signed_at", "ip_address")
    fields = ("role", "user", "name", "email", "signed_at", "ip_address")


class EDocumentSignatureBlockInline(admin.TabularInline):
    model = EDocumentSignatureBlock
    extra = 0
    readonly_fields = ("block_order", "block_type", "signer", "signed_at", "ip_address")
    fields = ("block_order", "block_type", "signer", "signed_at", "ip_address")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(EDocument)
class EDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "tenant", "lease", "sent_at", "completed_at", "is_locked")
    list_filter = ("status", "is_locked")
    search_fields = ("title", "content")
    raw_id_fields = ("template", "lease", "tenant", "property")
    readonly_fields = (
        "rendered_html", "sent_at", "completed_at", "final_pdf", "is_locked",
        "created_at", "updated_at", "created_by", "updated_by",
    )
    inlines = [EDocumentSignerInline, EDocumentSignatureBlockInline]

    fieldsets = (
        (None, {
            "fields": ("title", "template", "status")
        }),
        ("Attachments", {
            "fields": ("lease", "tenant", "property"),
        }),
        ("Content", {
            "fields": ("content", "rendered_html"),
            "classes": ("wide",),
        }),
        ("Lifecycle", {
            "fields": ("sent_at", "completed_at", "final_pdf", "is_locked"),
        }),
        ("Audit", {
            "fields": ("created_at", "updated_at", "created_by", "updated_by"),
            "classes": ("collapse",),
        }),
    )


@admin.register(EDocumentSigner)
class EDocumentSignerAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "document", "email", "signed_at", "ip_address")
    list_filter = ("role",)
    search_fields = ("name", "email", "document__title")
    raw_id_fields = ("document", "user")
    readonly_fields = ("signature_image", "signed_at", "ip_address", "user_agent")


@admin.register(EDocumentSignatureBlock)
class EDocumentSignatureBlockAdmin(admin.ModelAdmin):
    list_display = ("document", "signer", "block_type", "block_order", "signed_at")
    list_filter = ("block_type",)
    search_fields = ("document__title", "signer__name")
    raw_id_fields = ("document", "signer")
    readonly_fields = ("image", "signed_at", "ip_address")
