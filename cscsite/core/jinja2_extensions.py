from django.conf import settings
from django.urls import NoReverseMatch, reverse
from django.utils.translation import pgettext_lazy
from jinja2.ext import Extension
from treemenus.models import MenuItem, Menu

from menu_extension import CSCMENU_CACHE
from menu_extension.templatetags.csc_menu_tags import find_active_menu_items, \
    children, has_permissions


class Extensions(Extension):
    def __init__(self, environment):
        super().__init__(environment)
        environment.globals["csc_menu"] = csc_menu
        environment.globals["pagination"] = pagination


def csc_menu(request, menu_name, root_id=False):
    """Caching version of show_menu template tag."""
    if menu_name not in CSCMENU_CACHE:
        try:
            menu = Menu.objects.get(name=menu_name)
            flattened = list(MenuItem.objects.filter(menu__pk=menu.id)
                             .select_related('extension', )
                             .prefetch_related('extension__groups', )
                             .order_by('level', 'rank')
                             .all())
            for item in flattened:
                # FIXME: Not sure I can cache it, but don't use language support anyway
                item.caption = pgettext_lazy('menu', item.caption)
                # Groups list is empty if item available for all users.
                item.groups_allowed = [g.id for g in
                                       item.extension.groups.all()]
                # Override url from named_url if specified
                if item.named_url:
                    try:
                        item.url = reverse(item.named_url)
                    except NoReverseMatch as e:
                        if settings.DEBUG:
                            raise e
                        else:
                            item.url = "/#undefined"
            CSCMENU_CACHE[menu_name] = flattened
        except (MenuItem.DoesNotExist, Menu.DoesNotExist) as e:
            if settings.DEBUG:
                raise e
            else:
                return []
    else:
        flattened = CSCMENU_CACHE[menu_name]

    root_id = int(root_id)
    # Flattened to tree
    menu_tree = []
    user = request.user
    user_groups = user.get_cached_groups()
    for item in flattened:
        if not has_permissions(item, user, user_groups):
            continue
        # FIXME: What is root id?
        if root_id and item.level == 1 and item.id != root_id:
            continue
        if item.level == 1:
            item.children = children(item.id, flattened, user, user_groups)
            menu_tree.append(item)
        elif item.level > 1:
            # Items sorted by level
            break
    # For simplicity at the current time we have only one selected item.
    active_items = set()
    find_active_menu_items(menu_tree, request, active_items)
    return {
        "tree": menu_tree,
        "active_items": active_items
    }


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
