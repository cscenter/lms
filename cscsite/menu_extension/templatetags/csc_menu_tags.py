import re
import copy

from django import template
from django.conf import settings
from django.core.urlresolvers import reverse, NoReverseMatch

from treemenus.models import Menu, MenuItem

from .. import CSCMENU_CACHE

register = template.Library()


# TODO: Add nested level support
# FIXME: Remove deepcopy
# FIXME: Don't modify current list in `handle_selected`
@register.assignment_tag(takes_context=True)
def csc_menu(context, menu_name, root_id=False):
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
    for item in flattened:
        if not has_permissions(item, context['request'].user):
            continue
        # FIXME: What is root id?
        if root_id and item.level == 1 and item.id != root_id:
            continue
        if item.level == 1:
            item.children = children(item.id, flattened)
            menu_tree.append(item)
    # For simplicity at the current time we have only one selected item.
    active_items = set()
    find_active_menu_items(menu_tree, context['request'], active_items)
    return {
        "tree": menu_tree,
        "active_items": active_items
    }


def has_permissions(item, user, **kwargs):
    """Check user has permissions for view menu item"""
    if len(item.groups_allowed) > 0:
        if user.is_authenticated():
            user_groups = set(user._cs_group_pks)
        else:
            user_groups = set()
        if not user_groups.intersection(item.groups_allowed):
            return False
    if item.extension.unauthenticated and user.is_authenticated():
        return False
    if item.extension.protected and not user.is_authenticated():
        return False
    if item.extension.staff_only and not user.is_staff:
        return False
    return True


def children(parent_id, items):
    cs = [item for item in items if item.parent_id == parent_id]
    for c in cs:
        c.children = children(c.id, items)
    return cs


def find_active_menu_items(menu, request, active_items):
    for item in menu:
        if item.children:
            item_selected = find_active_menu_items(item.children, request,
                                                   active_items)
            if item_selected:
                active_items.add(item.id)
        if match_url(item, request.get_full_path()):
            active_items.add(item.id)
            return True
    return False


def match_url(item, current_url):
    for pattern in item.extension.exclude_patterns.strip().splitlines():
        if re.compile(pattern.strip()).match(current_url):
            return False
    for pattern in item.extension.select_patterns.strip().splitlines():
        if re.compile(pattern.strip()).match(current_url):
            return True
    if current_url.startswith(item.url):
        return True
    return False
