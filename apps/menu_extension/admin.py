from django.contrib import admin
from treemenus.admin import MenuAdmin, MenuItemAdmin
from treemenus.models import Menu

from .models import MenuItemExtension

# XXX: Too many queries in admin for treemenus package. Customize admin queryset for better perfomance

class MenuItemExtensionInline(admin.StackedInline):
    model = MenuItemExtension
    max_num = 1

class CustomMenuItemAdmin(MenuItemAdmin):
    inlines = [MenuItemExtensionInline, ]


class CustomMenuAdmin(MenuAdmin):
    menu_item_admin_class = CustomMenuItemAdmin

admin.site.unregister(Menu)
admin.site.register(Menu, CustomMenuAdmin)
