from django.db import models
from django.utils.translation import ugettext_lazy as _
from treemenus.models import MenuItem
from django.contrib.auth.models import Group


class MenuItemExtension(models.Model):
    menu_item = models.OneToOneField(MenuItem, related_name="extension", primary_key=True, on_delete=models.CASCADE)
    open_in_new_window = models.BooleanField(default=False, help_text=_("Open link in new tab is selected"))
    protected = models.BooleanField(default=False, help_text=_("Check if visible only for authenticated user"))
    unauthenticated = models.BooleanField(default=False, help_text=_("Check if visible only for unauthenticated user"))
    staff_only = models.BooleanField(default=False, help_text=_("Check if visible only for staff"))
    budge = models.CharField(help_text=_("Variable name for unred_notifications_cache"), max_length=255, blank=True, default="")
    classes = models.CharField(help_text=_("Additional classes"), max_length=255, blank=True, default="")
    groups = models.ManyToManyField(Group, verbose_name=_('groups'),
        blank=True, help_text=_('Restrict visibility to selected groups.'),
        related_name="menuitems_set", related_query_name="menuitem")
    select_patterns = models.TextField(blank=True, default=" ", help_text=_("Specify patterns when item is selected. One pattern for each line."))
    exclude_patterns = models.TextField(blank=True, default=" ", help_text=_("Specify patterns when item is not selected. One pattern for each line."))

    class Meta:
        verbose_name = _('Menu extensions')
        verbose_name_plural = _('Menu extensions')


from .signals import *
