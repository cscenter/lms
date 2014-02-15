from django.contrib import admin
from textpages.models import Textpage

class TextpageAdmin(admin.ModelAdmin):
    exclude = ['url_name', 'name']

admin.site.register(Textpage, TextpageAdmin)
