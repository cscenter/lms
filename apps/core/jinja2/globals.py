from crispy_forms.utils import render_crispy_form
from django.contrib.messages import get_messages, DEFAULT_LEVELS
from jinja2 import contextfunction
from menu import Menu


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


@contextfunction
def crispy(context, form):
    return render_crispy_form(form, context=context)


# FIXME not in use?
def pagination(page, request, **kwargs):
    range_length: int = kwargs.get("range", 10)
    assert range_length > 1
    url_param_name = kwargs.get("url_param_name", "page")
    url_get_params = kwargs.get("url_get_params", request.GET)

    # Calculate viewable page range
    page_count = page.paginator.num_pages
    current_page = page.number

    if range_length is None:
        range_min = 1
        range_max = page_count
    else:
        if range_length > page_count:
            range_length = page_count

        range_length -= 1
        range_min = max(current_page - (range_length // 2), 1)
        range_max = min(current_page + (range_length // 2), page_count)
        range_diff = range_max - range_min
        if range_diff < range_length:
            shift = range_length - range_diff
            if range_min - shift > 0:
                range_min -= shift
            else:
                range_max += shift

    page_range = range(range_min, range_max + 1)

    page_urls = []
    for page_num in page_range:
        url = _get_page_url(url_param_name, page_num, url_get_params)
        page_urls.append((page_num, url))

    first_page_url = None
    if current_page > 1:
        first_page_url = _get_page_url(url_param_name, 1, url_get_params)

    last_page_url = None
    if current_page < page_count:
        last_page_url = _get_page_url(url_param_name, page_count, url_get_params)

    return {
        'page': page,
        'first_page_url': first_page_url,
        'last_page_url': last_page_url,
        'page_urls': page_urls,
    }


def _get_page_url(url_param_name, page_num, url_get_params):
    url = ''
    url_params = url_get_params.copy()
    url_params[url_param_name] = page_num
    if len(url_params) > 0:
        url += '?' + url_params.urlencode()
    return url
