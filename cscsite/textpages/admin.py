from django.contrib import admin
from textpages.models import Textpage, CustomTextpage

from core.admin import UbereditorMixin


class TextpageAdmin(UbereditorMixin,
                    admin.ModelAdmin):
    exclude = ['url_name', 'name']
    readonly_fields = ['modified']


class CustomTextpageAdmin(UbereditorMixin,
                          admin.ModelAdmin):
    readonly_fields = ['modified']
    list_display = ['slug', 'name']


admin.site.register(Textpage, TextpageAdmin)
admin.site.register(CustomTextpage, CustomTextpageAdmin)
