from django.contrib import admin
from news.models import News

class NewsAdmin(admin.ModelAdmin):
    exclude = ['author']

    def save_model(self, request, obj, form, change):
        if not change:
            print request.user
            obj.author = request.user
        obj.save()

admin.site.register(News, NewsAdmin)
