from django.contrib import admin
from django.db import models as db_models

from core.widgets import AdminRichTextAreaWidget


class InternationalSchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'deadline', 'has_grants']
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }
