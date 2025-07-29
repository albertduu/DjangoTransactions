from django import template
from urllib.parse import urlencode

register = template.Library()

@register.simple_tag
def querystring(request, GET, param, value):
    params = GET.copy()
    params[param] = value
    return urlencode(params)
