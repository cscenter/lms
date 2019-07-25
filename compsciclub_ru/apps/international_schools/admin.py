from django.contrib import admin
from django.db import models as db_models

from core.widgets import AdminRichTextAreaWidget
from international_schools.models import InternationalSchool


@admin.register(InternationalSchool)
class InternationalSchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'deadline', 'has_grants']
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }
