import sys

import django
import re
import copy

from django import template
from django.conf import settings
from django.core.urlresolvers import reverse

from treemenus.models import Menu, MenuItem
from treemenus.config import APP_LABEL

from menu_extension import CSCMENU_CACHE
from menu_extension.models import MenuItemExtension

register = template.Library()


def csc_menu(context, menu_name):
    """Caching version of show_menu template tag"""
    # TODO: Multiple menu's cache
    if not CSCMENU_CACHE:
        try:
            menu = Menu.objects.get(name=menu_name)
            flattened = list(MenuItem.objects.filter(menu__pk=menu.id)
                                         .select_related('extension',)
                                         .prefetch_related('extension__groups',)
                                         .order_by('level', 'rank').all())
            for item in flattened:
                # Caching groups. Empty, if allowed for all groups
                item.groups_allowed = [g.id for g in item.extension.groups.all()]
                # Override url from named_url if specified
                if item.named_url:
                    item.url = reverse(item.named_url)
            CSCMENU_CACHE[:] = flattened
        except (MenuItem.DoesNotExist, Menu.DoesNotExist) as e:
            if settings.TEMPLATE_DEBUG:
                raise e
            else:
                return context
    else:
        flattened = CSCMENU_CACHE

    flattened_copy = copy.deepcopy(flattened)

    def allowed_for_user(item, user, **kwargs):
        """Validate item visibility for current user"""
        # Current user have no enough group permissions
        if len(item.groups_allowed) > 0:
            if user.is_authenticated():
                user_groups = set(context['request'].user._cs_group_pks)
            else:
                user_groups = set()
            if not set(user_groups).intersection(item.groups_allowed):
                return False
        if item.extension.unauthenticated and user.is_authenticated():
            return False
        if item.extension.protected and not user.is_authenticated():
            return False
        if item.extension.staff_only and not user.is_staff:
            return False
        return True


    # Flattened to tree
    menu_tree = []
    for item in flattened_copy:
        if not allowed_for_user(item, context['request'].user):
            continue
        if item.level == 1:
            item.children = children(item.id, flattened_copy)
            menu_tree.append(item)
    # For simplicity at the current time we have only one selected item.
    handle_selected(menu_tree, context['request'])
    context['menu'] = menu_tree
    context['menu_name'] = menu_name
    return context
register.inclusion_tag('menu.html', takes_context=True)(csc_menu)


def children(parent_id, items):
    cs = [item for item in items if item.parent_id == parent_id]
    for c in cs:
        c.children = children(c.id, items)
    return cs


def handle_selected(menu, request):
    class_selected = ' current'
    for item in menu:            
        if item.children:
            selected_item = handle_selected(item.children, request)
            if selected_item is not None:
                if class_selected not in item.extension.classes:
                    item.extension.classes += class_selected
        if match_url(item, request.get_full_path()):
            if class_selected not in item.extension.classes:
                item.extension.classes += class_selected
            return True


def match_url(item, current_url):
    for pattern in item.extension.exclude_patterns.strip().splitlines():
        if re.compile(pattern).match(current_url):
            return False
    for pattern in item.extension.select_patterns.strip().splitlines():
        if re.compile(pattern).match(current_url):
            return True
    if current_url.startswith(item.url):
        return True
    return False
