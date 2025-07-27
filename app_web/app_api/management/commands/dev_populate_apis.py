import os
import json

from django.core.management.base import BaseCommand
from django.conf import settings

from app_api.models import APIApp, API, CostOfLLMAppAI
from common.redis_logic.custom_redis import (
    get_redis_keys_by_pattern, delete_redis_key
)
from common.redis_logic.redis_schemas import REDIS_KEY_LLM_COST


APIs = {}


class Command(BaseCommand):
    @staticmethod
    def create_dummy_apis():

        json_files = [
            f for f in
            os.listdir("app_api/management/commands/api_apps")
            if f.endswith('.json')
        ]

        for json_file in json_files:
            with open(f"app_api/management/commands/api_apps/{json_file}", "r") as f:
                data = json.load(f)
                APIs.update(data)

        for key in APIs:
            category_obj = APIApp.objects.filter(display_name=key).first()
            if not category_obj:
                category_obj = APIApp.objects.create(
                    display_name=key,
                    display_order=APIs[key]["display_order"],
                    url_path=APIs[key]["url_path"],
                    description=APIs[key]["description"],
                )

            for api in APIs[key]["apis"]:
                if API.objects.filter( url_path=api["url_path"]).exists():
                    # update if local or dev
                    if settings.ENV_MODE in {"local", "dev"}:
                        api_obj = API.objects.get(url_path=api["url_path"])
                        api_obj.html_template_path = api["html_template_path"]
                        api_obj.api_app = category_obj
                        api_obj.display_name = api["display_name"]
                        api_obj.display_order = api["display_order"]
                        api_obj.description = api["description"]
                        api_obj.method = api["method"]
                        api_obj.cost = api.get("cost", 0)
                        api_obj.svg_icon_name = api.get("svg_icon_name", None)
                        api_obj.other_info = api.get("other_info", None)
                        api_obj.active = api.get("active", True)
                        api_obj.save()
                    continue

                API.objects.create(
                    html_template_path=api["html_template_path"],
                    api_app=category_obj,
                    display_name=api["display_name"],
                    display_order=api["display_order"],
                    description=api["description"],
                    url_path=api["url_path"],
                    method=api["method"],
                    cost=api.get("cost", 0),
                    svg_icon_name=api.get("svg_icon_name", None),
                    other_info=api.get("other_info", None),
                    active=api.get("active", True)
                )

    @staticmethod
    def populate_llm_api():
        with open(f"app_api/management/commands/ai_llm/cost_of_llm_api.json", "r") as f:
            data = json.load(f)

        # delete all keys
        keys = get_redis_keys_by_pattern(REDIS_KEY_LLM_COST.format(name="*"))
        for key in keys:
            delete_redis_key(key)

        # delete all objects in the table
        CostOfLLMAppAI.objects.all().delete()

        for k, v in data.items():
            CostOfLLMAppAI.objects.create(
                redis_key_name=v["redis_key_name"],
                display_name=v["display_name"],
                description=v.get("description", ""),
                display_order=v["display_order"],
                is_active=v["is_active"],
                cost=v["cost"],
                svg_icon_name=v.get("svg_icon_name", 0),
                other_info=v.get("other_info", {}),
            )

    def handle(self, *args, **kwargs):
        if settings.ENV_MODE not in {"local", "dev"}:
            self.stdout.write(
                self.style.ERROR(
                    "This command is only for Local and Dev environments."
                )
            )
            return
        self.create_dummy_apis()
        print("Dummy APIs have been created")
        self.populate_llm_api()
        print("Dummy LLM AI cost have been populated")
