from __future__ import absolute_import, unicode_literals

from bitfield import BitField
from dal import autocomplete
from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models as db_models
from django.utils.translation import ugettext_lazy as _
from modeltranslation.admin import TranslationAdmin

from core.admin import CityAwareModelForm, CityAwareAdminSplitDateTimeWidget, \
    CityAwareSplitDateTimeField
from core.compat import Django21BitFieldCheckboxSelectMultiple
from core.widgets import AdminRichTextAreaWidget, AdminRelatedDropdownFilter
from core.models import RelatedSpecMixin
from core.utils import admin_datetime, is_club_site
from learning.models import InternshipCategory
from learning.settings import PARTICIPANT_GROUPS
from users.models import CSCUser
from .models import Course, Semester, CourseOffering, Venue, \
    CourseClass, CourseClassAttachment, CourseOfferingNews, \
    Assignment, AssignmentAttachment, StudentAssignment, \
    AssignmentComment, Enrollment, NonCourseEvent, OnlineCourse, \
    CourseOfferingTeacher, InternationalSchool, Useful, Internship, AreaOfStudy, \
    StudyProgram, StudyProgramCourseGroup


class AreaOfStudyAdmin(TranslationAdmin, admin.ModelAdmin):
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


class StudyProgramAdmin(admin.ModelAdmin):
    list_filter = ["city", "year"]
    list_display = ["area", "city", "year"]
    inlines = [StudyProgramCourseGroupInline]
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }


class CourseAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ['name_ru', 'name_en']
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }


class CourseOfferingTeacherInline(admin.TabularInline):
    model = CourseOfferingTeacher
    extra = 0
    min_num = 1
    formfield_overrides = {
            BitField: {'widget': Django21BitFieldCheckboxSelectMultiple},
    }

    def formfield_for_foreignkey(self, db_field, *args, **kwargs):
        if db_field.name == "teacher":
            kwargs["queryset"] = CSCUser.objects.filter(groups__in=[
                PARTICIPANT_GROUPS.TEACHER_CENTER,
                PARTICIPANT_GROUPS.TEACHER_CLUB]).distinct()
        return super(CourseOfferingTeacherInline, self).formfield_for_foreignkey(db_field, *args, **kwargs)


class CourseOfferingAdminForm(forms.ModelForm):
    class Meta:
        model = CourseOffering
        fields = '__all__'

    def clean_is_open(self):
        is_open = self.cleaned_data['is_open']
        if is_club_site() and not is_open:
            raise ValidationError(_("You can create only open courses "
                                    "from CS club site"))
        return is_open


class CourseOfferingAdmin(TranslationAdmin, admin.ModelAdmin):
    list_filter = ['city', 'semester']
    list_display = ['course', 'semester', 'is_published_in_video', 'is_open']
    inlines = (CourseOfferingTeacherInline,)
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }
    form = CourseOfferingAdminForm


class CourseClassAttachmentAdmin(admin.ModelAdmin):
    list_filter = ['course_class']
    list_display = ['course_class', '__str__']


class CourseClassAttachmentInline(admin.TabularInline):
    model = CourseClassAttachment


class CourseClassAdmin(admin.ModelAdmin):
    save_as = True
    date_hierarchy = 'date'
    list_filter = ['type', 'venue']
    search_fields = ['course_offering__course__name']
    list_display = ['id', 'name', 'course_offering', 'date', 'venue', 'type']
    inlines = [CourseClassAttachmentInline]
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'course_offering':
            kwargs['queryset'] = (CourseOffering.objects
                                  .select_related("course", "semester"))
        return (super(CourseClassAdmin, self)
                .formfield_for_foreignkey(db_field, request, **kwargs))


class CourseOfferingNewsAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ['title', 'course_offering', 'created_local']
    raw_id_fields = ["course_offering", "author"]
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }

    def created_local(self, obj):
        return admin_datetime(obj.created_local())
    created_local.admin_order_field = 'created'
    created_local.short_description = _("Created")


class VenueAdminForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = '__all__'
        widgets = {
            'description': AdminRichTextAreaWidget(),
            'flags': Django21BitFieldCheckboxSelectMultiple()
        }


class VenueAdmin(admin.ModelAdmin):
    form = VenueAdminForm
    list_display = ['name', 'city']
    list_select_related = ["city"]


class AssignmentAdminForm(CityAwareModelForm):
    class Meta:
        model = Assignment
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        # We can select teachers only from related course offering
        if ('course_offering' in cleaned_data
                and 'notify_teachers' in cleaned_data
                and cleaned_data['notify_teachers']):
            co = cleaned_data['course_offering']
            co_teachers = [t.pk for t in co.courseofferingteacher_set.all()]
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
            'widget': CityAwareAdminSplitDateTimeWidget,
            'form_class': CityAwareSplitDateTimeField
        },
    }
    list_display = ['id', 'title', 'course_offering', 'created_local',
                    'deadline_at_local']
    search_fields = ['course_offering__course__name']

    def get_readonly_fields(self, request, obj=None):
        return ['course_offering'] if obj else []

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'course_offering':
            kwargs['queryset'] = (CourseOffering.objects
                .select_related("course", "semester"))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "notify_teachers":
            qs = (CourseOfferingTeacher.objects
                  .select_related("teacher", "course_offering"))
            try:
                assignment_pk = request.resolver_match.args[0]
                a = (Assignment.objects
                     .prefetch_related("course_offering__courseofferingteacher_set")
                     .get(pk=assignment_pk))
                teachers = [t.pk for t in a.course_offering.teachers.all()]
                qs = qs.filter(teacher__in=teachers,
                               course_offering=a.course_offering)
            except IndexError:
                pass
            kwargs["queryset"] = qs.order_by("course_offering_id").distinct()
        return super(AssignmentAdmin, self).formfield_for_manytomany(
            db_field, request, **kwargs)

    def save_related(self, request, form, formsets, change):
        if not change and not form.cleaned_data['notify_teachers']:
            co_teachers = form.cleaned_data['course_offering'].courseofferingteacher_set.all()
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


class AssignmentCommentAdmin(RelatedSpecMixin, admin.ModelAdmin):
    readonly_fields = ['student_assignment']
    list_display = ["get_assignment_name", "get_student", "author"]
    search_fields = ["student_assignment__assignment__title",
                     "student_assignment__assignment__id"]
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }
    related_spec = {
        'select': [
            ('student_assignment', [
                 ('assignment', [('course_offering', ['semester', 'course'])]),
                 'student'
             ]),
            'author'
        ]}

    def get_student(self, obj: AssignmentComment):
        return obj.student_assignment.student
    get_student.short_description = _("Assignment|assigned_to")

    def get_assignment_name(self, obj: AssignmentComment):
        return obj.student_assignment.assignment.title
    get_assignment_name.admin_order_field = 'student_assignment__assignment__title'
    get_assignment_name.short_description = _("Asssignment|name")


class EnrollmentAdmin(admin.ModelAdmin):
    form = CityAwareModelForm
    formfield_overrides = {
        db_models.DateTimeField: {
            'widget': CityAwareAdminSplitDateTimeWidget,
            'form_class': CityAwareSplitDateTimeField
        }
    }
    list_display = ['student', 'course_offering', 'is_deleted', 'grade',
                    'grade_changed_local']
    ordering = ['-pk']
    list_filter = [
        'course_offering__city_id',
        ('course_offering__semester', AdminRelatedDropdownFilter)
    ]
    search_fields = ['course_offering__course__name']
    exclude = ['grade_changed']
    raw_id_fields = ["student", "course_offering"]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['student', 'course_offering', 'grade_changed_local',
                    'modified']
        else:
            return ['grade_changed_local', 'modified']

    def grade_changed_local(self, obj):
        return admin_datetime(obj.grade_changed_local())
    grade_changed_local.admin_order_field = 'grade_changed'
    grade_changed_local.short_description = _("Enrollment|grade changed")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'student':
            kwargs['queryset'] = (get_user_model().objects
                                  .filter(groups__in=[
                                        PARTICIPANT_GROUPS.STUDENT_CENTER,
                                        PARTICIPANT_GROUPS.VOLUNTEER]))
        return (super(EnrollmentAdmin, self)
                .formfield_for_foreignkey(db_field, request, **kwargs))


class StudentAssignmentAdmin(RelatedSpecMixin, admin.ModelAdmin):
    list_display = ['student', 'assignment', 'grade', 'grade_changed', 'state']
    related_spec = {'select': [('assignment',
                                [('course_offering', ['semester', 'course'])]),
                               'student']}
    search_fields = ['student__last_name']
    raw_id_fields = ["assignment", "student"]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['student', 'assignment', 'grade_changed', 'state']
        else:
            return ['grade_changed', 'state']


class NonCourseEventAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    list_filter = ['venue']
    list_display = ['name', 'date', 'venue']


class OnlineCourseAdmin(admin.ModelAdmin):
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }


class InternationalSchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'deadline', 'has_grants']
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }


class UsefulAdmin(admin.ModelAdmin):
    list_filter = ['site']
    list_display = ['question', 'sort']


class InternshipCategoryAdmin(admin.ModelAdmin):
    list_filter = ['site']
    list_display = ['name', 'sort']


class InternshipAdmin(admin.ModelAdmin):
    list_select_related = ['category']
    list_filter = ['category']
    list_editable = ['sort']
    list_display = ['category', 'question', 'sort']


admin.site.register(AreaOfStudy, AreaOfStudyAdmin)
admin.site.register(StudyProgram, StudyProgramAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(OnlineCourse, OnlineCourseAdmin)
admin.site.register(InternationalSchool, InternationalSchoolAdmin)
admin.site.register(Semester)
admin.site.register(CourseOffering, CourseOfferingAdmin)
admin.site.register(Venue, VenueAdmin)
admin.site.register(CourseClass, CourseClassAdmin)
admin.site.register(CourseClassAttachment, CourseClassAttachmentAdmin)
admin.site.register(CourseOfferingNews, CourseOfferingNewsAdmin)
admin.site.register(Assignment, AssignmentAdmin)
admin.site.register(AssignmentAttachment, AssignmentAttachmentAdmin)
admin.site.register(StudentAssignment, StudentAssignmentAdmin)
admin.site.register(AssignmentComment, AssignmentCommentAdmin)
admin.site.register(Enrollment, EnrollmentAdmin)
admin.site.register(NonCourseEvent, NonCourseEventAdmin)
admin.site.register(Useful, UsefulAdmin)
admin.site.register(InternshipCategory, InternshipCategoryAdmin)
admin.site.register(Internship, InternshipAdmin)
