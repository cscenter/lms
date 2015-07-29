from __future__ import absolute_import, unicode_literals

from django.db import models
from django.dispatch import receiver


from . import CSCMENU_CACHE
from treemenus.models import MenuItem
from .models import MenuItemExtension


@receiver(models.signals.post_save, sender=MenuItem)
def menuitem_postsave(sender, created, instance, **kwargs):
    # Hook for creating menu item extension if extensions fields empty
    if created:
        menu_item_extension = MenuItemExtension(menu_item=instance)
        menu_item_extension.save()
    CSCMENU_CACHE.clear()
