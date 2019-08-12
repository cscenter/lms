from django.contrib import admin

from django.contrib import admin

from .models import Question, Category


class CategoryAdmin(admin.ModelAdmin):
    list_filter = ['site']
    list_display = ['name', 'sort']


class QuestionAdmin(admin.ModelAdmin):
    list_filter = ['site']
    list_display = ['question', 'sort']


admin.site.register(Question, QuestionAdmin)
admin.site.register(Category, CategoryAdmin)
