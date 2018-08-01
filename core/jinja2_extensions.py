from django.contrib.messages import get_messages, DEFAULT_LEVELS
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
        environment.globals["messages"] = messages


def csc_menu(request, menu_name, root_id=False):
    tree_menu = [
        MenuItem(caption='Проекты', url='/v1/pages/projects/')
    ]
    for i in tree_menu:
        i.extension = MockExtension()
        i.children = []
    return {
        "tree": tree_menu,
        "active_items": []
    }


def messages(request):
    messages_json = []
    for m in get_messages(request):
        if not m.extra_tags or "timeout" not in m.extra_tags:
            timeout = 0
        else:
            timeout = 2000
        if m.level == DEFAULT_LEVELS["WARNING"]:
            message_level = 'warning'
        elif m.level == DEFAULT_LEVELS["ERROR"]:
            message_level = 'error'
        elif m.level == DEFAULT_LEVELS["SUCCESS"]:
            message_level = 'success'
        else:
            message_level = 'info'
        messages_json.append({"text": m.message, "timeout": timeout, "type": message_level})
    return messages_json
