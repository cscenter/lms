from crispy_forms.utils import render_crispy_form

from django.contrib.messages import DEFAULT_LEVELS, get_messages

from core.menu import Menu
from jinja2 import pass_context


def messages(request):
    """
    Returns one-time notification messages in a format convenient for
    js notification libraries (e.g. `noty`)
    """
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
        messages_json.append({
            "text": m.message,
            "timeout": timeout,
            "type": message_level
        })
    return messages_json


def generate_menu(menu_name, request, root_id=None):
    return Menu.process(request, name=menu_name)


@pass_context
def crispy(context, form):
    return render_crispy_form(form, context=context)
