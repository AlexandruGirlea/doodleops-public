from app_settings.models import Setting


def get_setting(key, default=None, expected_type=None):
    try:
        setting = Setting.objects.get(key=key)
        value = setting.get_value()
    except Setting.DoesNotExist:
        return default
    except Exception:
        return default
    if expected_type and not isinstance(value, expected_type):
        raise ValueError(f"Setting {key} is not of type {expected_type}.")
    return value
