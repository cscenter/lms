from bitfield import BitField
from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import models as db_models
from django.utils.translation import ugettext_lazy as _
from modeltranslation.admin import TranslationAdmin

from core.admin import TimezoneAwareModelForm, \
    TimezoneAwareAdminSplitDateTimeWidget, \
    TimezoneAwareSplitDateTimeField
from core.compat import Django21BitFieldCheckboxSelectMultiple
from core.utils import is_club_site, admin_datetime
from core.widgets import AdminRichTextAreaWidget
from courses.models import CourseTeacher, Course, CourseClassAttachment, \
    Assignment, MetaCourse, Semester, CourseClass, CourseNews, \
    AssignmentAttachment
from users.constants import Roles
from users.models import User


class SemesterAdmin(admin.ModelAdmin):
    ordering = ('-index',)


class MetaCourseAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ['name_ru', 'name_en']
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }


class CourseTeacherInline(admin.TabularInline):
    model = CourseTeacher
    extra = 0
    min_num = 1
    formfield_overrides = {
            BitField: {'widget': Django21BitFieldCheckboxSelectMultiple},
    }

    def formfield_for_foreignkey(self, db_field, *args, **kwargs):
        if db_field.name == "teacher":
            kwargs["queryset"] = (User.objects
                                  .has_role(Roles.TEACHER)
                                  .distinct())
        return super().formfield_for_foreignkey(db_field, *args, **kwargs)


class CourseAdminForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = '__all__'

    def clean_is_open(self):
        is_open = self.cleaned_data['is_open']
        if is_club_site() and not is_open:
            raise ValidationError(_("You can create only open courses "
                                    "from CS club site"))
        return is_open


class CourseAdmin(TranslationAdmin, admin.ModelAdmin):
    list_filter = ['city', 'semester']
    list_display = ['meta_course', 'semester', 'is_published_in_video',
                    'is_open']
    inlines = (CourseTeacherInline,)
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }
    form = CourseAdminForm


class CourseClassAttachmentAdmin(admin.ModelAdmin):
    list_filter = ['course_class']
    list_display = ['course_class', '__str__']


class CourseClassAttachmentInline(admin.TabularInline):
    model = CourseClassAttachment


class CourseClassAdmin(admin.ModelAdmin):
    save_as = True
    date_hierarchy = 'date'
    list_filter = ['type', 'venue']
    search_fields = ['course__meta_course__name']
    list_display = ['id', 'name', 'course', 'date', 'venue', 'type']
    inlines = [CourseClassAttachmentInline]
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'course':
            kwargs['queryset'] = (Course.objects
                                  .select_related("meta_course", "semester"))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class CourseNewsAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ['title', 'course', 'created_local']
    raw_id_fields = ["course", "author"]
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }

    def created_local(self, obj):
        return admin_datetime(obj.created_local())
    created_local.admin_order_field = 'created'
    created_local.short_description = _("Created")


class AssignmentAdminForm(TimezoneAwareModelForm):
    class Meta:
        model = Assignment
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        # We can select teachers only from related course offering
        if ('course' in cleaned_data
                and 'notify_teachers' in cleaned_data
                and cleaned_data['notify_teachers']):
            co = cleaned_data['course']
            co_teachers = [t.pk for t in co.course_teachers.all()]
            if any(t.pk not in co_teachers for t in cleaned_data['notify_teachers']):
                self.add_error('notify_teachers', ValidationError(
                        _("Assignment|Please, double check teachers list. Some "
                          "of them not related to selected course offering")))


class AssignmentAttachmentAdmin(admin.ModelAdmin):
    raw_id_fields = ["assignment"]


class AssignmentAdmin(admin.ModelAdmin):
    form = AssignmentAdminForm
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
        db_models.DateTimeField: {
            'widget': TimezoneAwareAdminSplitDateTimeWidget,
            'form_class': TimezoneAwareSplitDateTimeField
        },
    }
    list_display = ['id', 'title', 'course', 'created_local',
                    'deadline_at_local']
    search_fields = ['course__meta_course__name']

    def get_readonly_fields(self, request, obj=None):
        return ['course'] if obj else []

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'course':
            kwargs['queryset'] = (Course.objects
                                  .select_related("meta_course", "semester"))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "notify_teachers":
            qs = (CourseTeacher.objects
                  .select_related("teacher", "course"))
            try:
                assignment_pk = request.resolver_match.args[0]
                a = (Assignment.objects
                     .prefetch_related("course__course_teachers")
                     .get(pk=assignment_pk))
                teachers = [t.pk for t in a.course.teachers.all()]
                qs = qs.filter(teacher__in=teachers,
                               course=a.course)
            except IndexError:
                pass
            kwargs["queryset"] = qs.order_by("course_id").distinct()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def save_related(self, request, form, formsets, change):
        if not change and not form.cleaned_data['notify_teachers']:
            co_teachers = form.cleaned_data['course'].course_teachers.all()
            form.cleaned_data['notify_teachers'] = [t.pk for t in co_teachers if t.notify_by_default]
        return super().save_related(request, form, formsets, change)

    def created_local(self, obj):
        return admin_datetime(obj.created_local())
    created_local.admin_order_field = 'created'
    created_local.short_description = _("Created")

    def deadline_at_local(self, obj):
        return admin_datetime(obj.deadline_at_local())
    deadline_at_local.admin_order_field = 'deadline_at'
    deadline_at_local.short_description = _("Assignment|deadline")


admin.site.register(MetaCourse, MetaCourseAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Semester, SemesterAdmin)
admin.site.register(CourseClass, CourseClassAdmin)
admin.site.register(CourseClassAttachment, CourseClassAttachmentAdmin)
admin.site.register(CourseNews, CourseNewsAdmin)
admin.site.register(Assignment, AssignmentAdmin)
admin.site.register(AssignmentAttachment, AssignmentAttachmentAdmin)
