from django.contrib import admin
from textpages.models import Textpage

from core.admin import UbereditorMixin


class TextpageAdmin(UbereditorMixin,
                    admin.ModelAdmin):
    exclude = ['url_name', 'name']

admin.site.register(Textpage, TextpageAdmin)
