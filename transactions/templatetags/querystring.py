# transactions/templatetags/querystring.py

from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    """
    Custom template tag to build query string while replacing keys.
    Usage: {% querystring page=2 %}
    """
    request = context['request']
    updated = request.GET.copy()
    for key, value in kwargs.items():
        updated[key] = value
    return updated.urlencode()
