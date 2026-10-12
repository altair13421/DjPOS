from django.contrib import admin

from .models import Organization, OrganizationMembership, Settings, UserLog


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "is_active",
        "allow_debug_superusers",
        "created_at",
    )
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly_fields.append("allow_debug_superusers")
        return readonly_fields


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "is_default", "is_debug_access")
    list_filter = ("role", "organization")
    search_fields = ("user__username", "organization__name")
    readonly_fields = ("is_debug_access",)


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ("organization", "store_name", "store_category", "currency", "owner_name")


@admin.register(UserLog)
class UserLogAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "reason", "created_at", "notes")
    list_filter = ("reason", "organization", "created_at")
    search_fields = ("user__username", "notes")
    readonly_fields = ("created_at",)
