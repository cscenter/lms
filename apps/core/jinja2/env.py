from jinja2 import Environment

from core.context_processors import get_common_template_context


def environment(**options):
    env = Environment(**options)
    env.globals.update(get_common_template_context())
    return env
