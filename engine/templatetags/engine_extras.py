# engine/templatetags/engine_extras.py
from django import template

register = template.Library()

@register.filter
def get_item(obj, key):
    """
    Safe dict/list lookup for templates.
    - If obj is a dict, return obj.get(key, "")
    - If obj is a list/tuple and key is an int, return obj[int(key)]
    - Otherwise return ""
    """
    try:
        if isinstance(obj, dict):
            return obj.get(key, "")
        try:
            i = int(key)
            return obj[i]
        except Exception:
            return ""
    except Exception:
        return ""
