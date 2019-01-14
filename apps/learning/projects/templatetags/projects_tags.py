from django.template import Library

register = Library()


@register.filter
def lookup_display(value, arg):
    """Returns get_<attr>_display() if exists, attr value otherwise"""
    if hasattr(value, "get_{}_display".format(arg)):
        return getattr(value, "get_{}_display".format(arg))()
    elif hasattr(value, str(arg)):
        return getattr(value, str(arg))
    return None


@register.filter
def verbose_name_by_attr_name(model, attr_name):
    """Returns get_<attr>_display() if exists, attr value otherwise"""
    return model._meta.get_field(attr_name).verbose_name

