from django.conf import settings
from django.urls import NoReverseMatch, reverse
from django.utils.translation import pgettext_lazy
from jinja2.ext import Extension
from treemenus.models import MenuItem, Menu

from menu_extension import CSCMENU_CACHE
from menu_extension.templatetags.csc_menu_tags import find_active_menu_items, \
    children, has_permissions


class MenuExtension(Extension):
    def __init__(self, environment):
        super().__init__(environment)
        environment.globals["csc_menu"] = csc_menu


def csc_menu(request, menu_name, root_id=False):
    """Caching version of show_menu template tag."""
    if menu_name not in CSCMENU_CACHE:
        try:
            menu = Menu.objects.get(name=menu_name)
            flattened = list(MenuItem.objects.filter(menu__pk=menu.id)
                             .select_related('extension',)
                             .prefetch_related('extension__groups',)
                             .order_by('level', 'rank')
                             .all())
            for item in flattened:
                # FIXME: Not sure I can cache it, but don't use language support anyway
                item.caption = pgettext_lazy('menu', item.caption)
                # Groups list is empty if item available for all users.
                item.groups_allowed = [g.id for g in item.extension.groups.all()]
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