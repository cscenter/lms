from django import template

register = template.Library()

@register.filter
def getbykey(x, key):
    return x[key]
