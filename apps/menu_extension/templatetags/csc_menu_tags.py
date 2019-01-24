import re
import copy

from django import template
from django.conf import settings
from django.urls import reverse, NoReverseMatch
from django.utils.translation import pgettext_lazy

from treemenus.models import Menu, MenuItem

from .. import CSCMENU_CACHE

register = template.Library()


# TODO: Add nested level support
@register.simple_tag(takes_context=True)
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
    user = context['request'].user
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
    find_active_menu_items(menu_tree, context['request'], active_items)
    return {
        "tree": menu_tree,
        "active_items": active_items
    }


def has_permissions(menu_item, user, user_groups, **kwargs):
    """Check user has permissions for view menu item"""
    if menu_item.extension.unauthenticated and user.is_authenticated:
        return False
    if menu_item.extension.protected and not user.is_authenticated:
        return False
    if menu_item.extension.staff_only and not user.is_staff:
        return False
    if len(menu_item.groups_allowed) > 0:
        if not user_groups.intersection(menu_item.groups_allowed):
            return False
        restricted_to_students = {
            user.roles.STUDENT_CENTER,
            user.roles.VOLUNTEER
        }
        if (restricted_to_students.intersection(menu_item.groups_allowed) and
                not user.is_active_student):
            return False
    return True


def children(parent_id, items, user, user_groups):
    cs = [i for i in items
          if i.parent_id == parent_id and has_permissions(i, user, user_groups)]
    for c in cs:
        c.children = children(c.id, items, user, user_groups)
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
