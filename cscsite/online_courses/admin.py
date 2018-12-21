from django.contrib import admin
from django.db import models as db_models

from core.widgets import AdminRichTextAreaWidget
from online_courses.models import OnlineCourse


class OnlineCourseAdmin(admin.ModelAdmin):
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }

admin.site.register(OnlineCourse, OnlineCourseAdmin)
