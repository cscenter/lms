from django import template
from django.utils.translation import ugettext_lazy as _

register = template.Library()


@register.simple_tag
def class_materials(course_class):
    """
    A tag for displaying a list of materials for particular course class
    """
    pass
