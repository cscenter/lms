from django.utils.translation import pgettext_lazy
from jinja2.ext import Extension
from treemenus.models import MenuItem, Menu


class MockExtension:
    open_in_new_window = False
    budge = None
    classes = ''


class MenuExtension(Extension):
    def __init__(self, environment):
        super().__init__(environment)
        environment.globals["csc_menu"] = csc_menu


def csc_menu(request, menu_name, root_id=False):
    tree_menu = [
        MenuItem(caption='Test', url='/pages/')
    ]
    for i in tree_menu:
        i.extension = MockExtension()
        i.children = []
    return {
        "tree": tree_menu,
        "active_items": []
    }
