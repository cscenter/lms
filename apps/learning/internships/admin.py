from django.contrib import admin

from learning.internships.models import InternshipCategory, Internship


class InternshipCategoryAdmin(admin.ModelAdmin):
    list_filter = ['site']
    list_display = ['name', 'sort']


class InternshipAdmin(admin.ModelAdmin):
    list_select_related = ['category']
    list_filter = ['category']
    list_editable = ['sort']
    list_display = ['category', 'question', 'sort']


admin.site.register(InternshipCategory, InternshipCategoryAdmin)
admin.site.register(Internship, InternshipAdmin)
