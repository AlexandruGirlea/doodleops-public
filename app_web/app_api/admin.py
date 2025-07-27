from django.contrib import admin

from app_api.models import APIApp, API, APICounter, CostOfLLMAppAI


class AdminAPIApp(admin.ModelAdmin):
    list_display = ("display_name", "url_path", "description", "display_order")

    # display order by `display_order`
    ordering = ("display_order",)


class AminAPI(admin.ModelAdmin):
    list_display = (
        "display_name",
        "active",
        "api_app",
        "html_template_path",
        "description",
        "url_path",
    )

    search_fields = ("display_name", "description")


class AdminAPICounter(admin.ModelAdmin):
    list_display = (
        "username",
        "api_name",
        "number_of_calls",
        "date",
        "credits_used",
        "created",
    )

    # filtering by username
    list_filter = ("username",)

    search_fields = ("username", "api_name")


class AdminCostOfLLMAppAI(admin.ModelAdmin):
    list_display = (
        "display_name",
        "display_order",
        "is_active",
        "cost",
        "svg_icon_name",
    )

    # display order by `display_order`
    ordering = ("display_order",)

    def delete_model(self, request, obj):
        # this runs when you push the delete button on the Admin obj view
        obj.delete()  # Calls your custom delete() method

    def delete_queryset(self, request, queryset):
        # this is run when you try to delete one or multiple obj from the main
        # dashboard
        for obj in queryset:
            obj.delete()


admin.site.register(APIApp, AdminAPIApp)
admin.site.register(API, AminAPI)
admin.site.register(APICounter, AdminAPICounter)
admin.site.register(CostOfLLMAppAI, AdminCostOfLLMAppAI)
