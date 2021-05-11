from django import template

from core.menu import Menu

register = template.Library()


# TODO: Add nested level support
@register.simple_tag(takes_context=True)
def csc_menu(context, menu_name, root_id=False):
    if 'request' not in context:
        return '<!-- menu failed to render due to missing request -->'
    visible_menu = Menu.process(context['request'], name=menu_name)
    return visible_menu
