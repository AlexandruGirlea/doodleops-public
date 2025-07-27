import uuid
from django.db import models
from django.core.exceptions import ValidationError

from common.redis_logic.custom_redis import set_redis_key, delete_redis_key
from common.redis_logic.redis_schemas import (
    REDIS_KEY_API_COST, REDIS_KEY_LLM_COST
)


class HTTPMethod(models.TextChoices):
    GET = 'GET', 'GET'
    POST = 'POST', 'POST'
    PUT = 'PUT', 'PUT'
    DELETE = 'DELETE', 'DELETE'


class APIApp(models.Model):
    display_name = models.CharField(max_length=100, unique=True)
    display_order = models.IntegerField(default=0, unique=True)
    url_path = models.CharField(max_length=100, unique=True)
    description = models.TextField(max_length=1000, blank=True, null=True)

    def __str__(self):
        return format(self.display_name)

    class Meta:
        verbose_name_plural = "API Apps"


class API(models.Model):
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    html_template_path = models.CharField(
        max_length=100, help_text=(
            "The path to the HTML template rendered when the API is called."
            )
        )
    api_app = models.ForeignKey(
        APIApp, on_delete=models.DO_NOTHING, related_name="apis",
        help_text="The API App this API belongs to."
    )
    display_name = models.CharField(max_length=100, unique=True)
    display_order = models.IntegerField(default=0)
    url_path = models.CharField(
        max_length=255, unique=True,
        help_text="The URL path to call this API from FastAPI"
    )
    doc_url_path = models.CharField(
        max_length=255, unique=True, blank=True, null=True,
        help_text="The URL path to the documentation of this API"
    )
    description = models.TextField(max_length=1000, blank=True, null=True)
    method = models.CharField(
        max_length=6,
        choices=HTTPMethod.choices,
        default=HTTPMethod.GET,
        help_text="Choose an HTTP method for this API"
    )
    active = models.BooleanField(default=True)
    cost = models.IntegerField(default=0, blank=True, null=True)
    svg_icon_name = models.CharField(max_length=100, unique=False, blank=True, null=True)
    other_info = models.JSONField(blank=True, null=True)

    def __str__(self):
        return format(self.display_name)

    def save(self, *args, **kwargs):
        # we need to remove the .html from the name for use in Redis
        if (
                self.html_template_path.endswith(".html") and
                " " not in self.html_template_path
        ):
            self.name = self.html_template_path[:-5]
        else:
            raise ValidationError("The HTML template path must end with .html")

        set_redis_key(
            key=REDIS_KEY_API_COST.format(api_name=self.name),
            simple_value=str(self.cost),
        )
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "APIs"


class APICounter(models.Model):
    """
    This is not meant to be directly connected to other Tables.

    This is meant to be used for billing/archival purposes.

    The date field is used to identify on which day the API was called,
    because the billing cycle is between fixed dates, not between
    timestamps or datetime objects. See the `ReadMe.md` for more info.

    OBS: in Django `DateField` is not timezone-aware.
    """

    username = models.CharField(max_length=100)
    api_name = models.CharField(max_length=255)
    number_of_calls = models.IntegerField(default=0)
    date = models.DateField()  # see above
    credits_used = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} - {self.api_name} - {self.date}"

    class Meta:
        verbose_name_plural = "API Calls Counter"
        unique_together = ["username", "api_name", "date"]


class CostOfLLMAppAI(models.Model):
    redis_key_name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(max_length=1000, blank=True, null=True)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    cost = models.IntegerField()
    svg_icon_name = models.CharField(
        max_length=100, unique=False, blank=True, null=True
    )
    other_info = models.JSONField(blank=True, null=True)

    def __str__(self):
        return format(self.display_name)

    def save(self, *args, **kwargs):
        set_redis_key(
            key=REDIS_KEY_LLM_COST.format(name=self.redis_key_name),
            simple_value=str(self.cost),
        )
        super().save(*args, **kwargs)

    # when deleting also delete the redis key
    def delete(self, *args, **kwargs):
        delete_redis_key(
            key=REDIS_KEY_LLM_COST.format(name=self.redis_key_name),
        )
        super().delete(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Cost of LLMs APP AI"
