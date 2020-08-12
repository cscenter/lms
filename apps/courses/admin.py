from bitfield import BitField
from bitfield.forms import BitFieldCheckboxSelectMultiple
from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import models as db_models
from django.forms import BaseInlineFormSet
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationAdmin

from core.models import Branch
from core.timezone import TimezoneAwareDateTimeField
from core.timezone.forms import TimezoneAwareAdminForm, \
    TimezoneAwareAdminSplitDateTimeWidget, TimezoneAwareSplitDateTimeField
from core.utils import is_club_site, admin_datetime
from core.widgets import AdminRichTextAreaWidget
from courses.models import CourseTeacher, Course, CourseClassAttachment, \
    Assignment, MetaCourse, Semester, CourseClass, CourseNews, \
    AssignmentAttachment, LearningSpace, CourseReview, CourseBranch
from courses.services import CourseService
from learning.models import AssignmentGroup, StudentGroup, EnrollmentPeriod
from learning.services import AssignmentService


class EnrollmentPeriodInline(admin.StackedInline):
    model = EnrollmentPeriod
    extra = 0


class SemesterAdmin(admin.ModelAdmin):
    ordering = ('-index',)
    readonly_fields = ('starts_at', 'ends_at')
    inlines = [EnrollmentPeriodInline]


class MetaCourseAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ['name_ru', 'name_en']
    search_fields = ('name_ru', 'name_en')
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }


class CourseReviewAdmin(admin.ModelAdmin):
    search_fields = ('course__meta_course__name',)
    list_display = ('course', 'author')
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }
    raw_id_fields = ('author', 'course')


class CourseTeacherInline(admin.TabularInline):
    model = CourseTeacher
    extra = 0
    min_num = 1
    raw_id_fields = ('teacher',)
    formfield_overrides = {
        BitField: {'widget': BitFieldCheckboxSelectMultiple},
    }
    # FIXME: customize template (hide link `show on site`, now it's hidden by css)


class CourseBranchFormSet(BaseInlineFormSet):
    def save(self, commit=True):
        saved_objects = super().save(commit)
        if commit:
            CourseService.sync_branches(course=self.instance)
        return saved_objects


class CourseBranchInline(admin.TabularInline):
    model = CourseBranch
    formset = CourseBranchFormSet
    extra = 0
    min_num = 0

    def formfield_for_foreignkey(self, db_field, *args, **kwargs):
        if db_field.name == "branch":
            kwargs["queryset"] = (Branch.objects.select_related('site'))
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
    form = CourseAdminForm
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }
    exclude = ('additional_branches',)
    list_filter = ['main_branch', 'semester']
    list_display = ['meta_course', 'semester', 'is_published_in_video',
                    'is_open']
    inlines = (CourseBranchInline, CourseTeacherInline,)
    raw_id_fields = ('meta_course',)

    class Media:
        css = {
            'all': ('v2/css/django_admin.css',)
        }


class LearningSpaceAdmin(admin.ModelAdmin):
    list_filter = ('branch',)
    list_display = ['location', 'order']
    list_select_related = ('location',)


class CourseClassAttachmentAdmin(admin.ModelAdmin):
    list_filter = ['course_class']
    list_display = ['course_class', '__str__']


class CourseClassAttachmentInline(admin.TabularInline):
    model = CourseClassAttachment


class CourseClassAdmin(admin.ModelAdmin):
    save_as = True
    date_hierarchy = 'date'
    list_filter = ['type']
    search_fields = ['course__meta_course__name']
    list_display = ['id', 'name', 'course', 'date', 'type']
    raw_id_fields = ['venue']
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


class AssignmentAdminForm(TimezoneAwareAdminForm):
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
                        _("Please, double check teacher list. Some "
                          "users are not related to the selected course")))


class AssignmentAttachmentAdmin(admin.ModelAdmin):
    raw_id_fields = ["assignment"]


class AssignmentGroupInline(admin.TabularInline):
    model = AssignmentGroup
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "group":
            qs = StudentGroup.objects.select_related("course")
            try:
                assignment_id = request.resolver_match.kwargs['object_id']
                a = Assignment.objects.get(pk=assignment_id)
                qs = qs.filter(course_id=a.course_id)
            except KeyError:
                pass
            kwargs["queryset"] = qs.order_by("name").distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class AssignmentAdmin(admin.ModelAdmin):
    form = AssignmentAdminForm
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
        TimezoneAwareDateTimeField: {
            'widget': TimezoneAwareAdminSplitDateTimeWidget,
            'form_class': TimezoneAwareSplitDateTimeField
        },
    }
    raw_id_fields = ('course',)
    list_display = ['id', 'title', 'course', 'created_local',
                    'deadline_at_local']
    search_fields = ['course__meta_course__name']

    def get_readonly_fields(self, request, obj=None):
        return ['course'] if obj else []

    def get_exclude(self, request, obj=None):
        return None if obj else ('notify_teachers',)

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "notify_teachers":
            qs = CourseTeacher.objects.select_related("teacher", "course")
            try:
                assignment_id = request.resolver_match.kwargs['object_id']
                a = Assignment.objects.get(pk=assignment_id)
                qs = qs.filter(course_id=a.course_id)
            except KeyError:
                pass
            kwargs["queryset"] = qs.order_by("course_id").distinct()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        created = not change
        if created:
            AssignmentService.bulk_create_student_assignments(form.instance)
            AssignmentService.setup_notification_settings(form.instance)

    def created_local(self, obj):
        return admin_datetime(obj.created_local())
    created_local.admin_order_field = 'created'
    created_local.short_description = _("Created")

    def deadline_at_local(self, obj):
        return admin_datetime(obj.deadline_at_local())
    deadline_at_local.admin_order_field = 'deadline_at'
    deadline_at_local.short_description = _("Assignment|deadline")


admin.site.register(CourseReview, CourseReviewAdmin)
admin.site.register(MetaCourse, MetaCourseAdmin)
admin.site.register(Semester, SemesterAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(CourseNews, CourseNewsAdmin)
admin.site.register(LearningSpace, LearningSpaceAdmin)
admin.site.register(CourseClass, CourseClassAdmin)
admin.site.register(CourseClassAttachment, CourseClassAttachmentAdmin)
admin.site.register(Assignment, AssignmentAdmin)
admin.site.register(AssignmentAttachment, AssignmentAttachmentAdmin)
