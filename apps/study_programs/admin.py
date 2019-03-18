from dal import autocomplete
from django.contrib import admin

from django.db import models as db_models
from modeltranslation.admin import TranslationAdmin

from core.widgets import AdminRichTextAreaWidget
from study_programs.models import StudyProgramCourseGroup, AcademicDiscipline, \
    StudyProgram


@admin.register(AcademicDiscipline)
class AcademicDisciplineAdmin(TranslationAdmin, admin.ModelAdmin):
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }


class StudyProgramCourseGroupInline(admin.TabularInline):
    model = StudyProgramCourseGroup
    extra = 0
    formfield_overrides = {
        db_models.ManyToManyField: {'widget': autocomplete.Select2Multiple()}
    }

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        form = formset.form
        form.base_fields['courses'].widget.can_add_related = False
        form.base_fields['courses'].widget.can_change_related = False
        return formset


@admin.register(StudyProgram)
class StudyProgramAdmin(admin.ModelAdmin):
    list_filter = ["branch", "year", "is_active"]
    list_display = ["academic_discipline", "branch", "year", "is_active"]
    inlines = [StudyProgramCourseGroupInline]
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }
