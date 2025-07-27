from django import forms
import json


class PrettyJSONWidget(forms.Textarea):
    def format_value(self, value):
        try:
            # This will format the JSON string with indentation
            return json.dumps(json.loads(value), indent=4, sort_keys=True)
        except (ValueError, TypeError):
            # If the value is not valid JSON, it will return the original value
            return super().format_value(value)
