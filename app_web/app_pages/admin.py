from django.contrib import admin

from app_pages.models import SuggestNewFeature, BlogPost, BlogCategory


class SuggestNewFeatureAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user")
    search_fields = ("user__email",)
    ordering = ("-created_at",)

    readonly_fields = ("user", "feature_description", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        """
        Disable bulk delete_selected action
        """
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


admin.site.register(BlogPost)
admin.site.register(BlogCategory)
admin.site.register(SuggestNewFeature, SuggestNewFeatureAdmin)

admin.site.site_header = "DoodleOps Dashboard"
admin.site.site_title = "DoodleOps Dashboard"
admin.site.index_title = "Welcome to DoodleOps Dashboard"