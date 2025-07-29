from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    """
    Update query string params while preserving others.
    Usage: {% querystring page=2 %}
    """
    request = context['request']
    query = request.GET.copy()
    for k, v in kwargs.items():
        if v is None:
            query.pop(k, None)
        else:
            query[k] = v
    return query.urlencode()