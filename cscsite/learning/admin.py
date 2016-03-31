from __future__ import absolute_import, unicode_literals

from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from modeltranslation.admin import TranslationAdmin

from core.admin import UbereditorMixin, WiderLabelsMixin
from core.models import apply_related_spec
from users.models import CSCUser
from .models import Course, Semester, CourseOffering, Venue, \
    CourseClass, CourseClassAttachment, CourseOfferingNews, \
    Assignment, AssignmentAttachment, StudentAssignment, \
    AssignmentComment, Enrollment, NonCourseEvent, StudentProject, OnlineCourse, \
    CourseOfferingTeacher, InternationalSchool, Useful
from learning.settings import PARTICIPANT_GROUPS
from bitfield import BitField
from bitfield.forms import BitFieldCheckboxSelectMultiple


class RelatedSpecMixin(object):
    def get_queryset(self, request):
        qs = super(RelatedSpecMixin, self).get_queryset(request)
        return apply_related_spec(qs, self.related_spec)


class CourseAdmin(TranslationAdmin, UbereditorMixin, admin.ModelAdmin):
    pass


class CourseOfferingTeacherInline(admin.TabularInline):
    model = CourseOfferingTeacher
    extra = 0
    formfield_overrides = {
            BitField: {'widget': BitFieldCheckboxSelectMultiple},
    }

    def formfield_for_foreignkey(self, db_field, *args, **kwargs):
        if db_field.name == "teacher":
            kwargs["queryset"] = CSCUser.objects.filter(groups__in=[
                PARTICIPANT_GROUPS.TEACHER_CENTER,
                PARTICIPANT_GROUPS.TEACHER_CLUB]).distinct()
        return super(CourseOfferingTeacherInline, self).formfield_for_foreignkey(db_field, *args, **kwargs)

class CourseOfferingAdmin(UbereditorMixin, WiderLabelsMixin, TranslationAdmin,
                          admin.ModelAdmin):
    list_filter = ['course', 'semester']
    list_display = ['course', 'semester', 'is_published_in_video', 'is_open']
    inlines = (CourseOfferingTeacherInline,)


class CourseClassAttachmentAdmin(admin.ModelAdmin):
    list_filter = ['course_class']
    list_display = ['course_class', '__str__']


class CourseClassAttachmentInline(admin.TabularInline):
    model = CourseClassAttachment


class CourseClassAdmin(UbereditorMixin, admin.ModelAdmin):
    save_as = True
    date_hierarchy = 'date'
    list_filter = ['course_offering', 'venue', 'type']
    list_display = ['name', 'course_offering', 'date', 'venue', 'type']
    inlines = [CourseClassAttachmentInline]


class CourseOfferingNewsAdmin(UbereditorMixin, admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ['title', 'course_offering', 'created']


class VenueAdmin(UbereditorMixin, admin.ModelAdmin):
    pass


class AssignmentAdminForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = '__all__'

    def clean(self):
        cleaned_data = super(AssignmentAdminForm, self).clean()
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


class AssignmentAdmin(UbereditorMixin, admin.ModelAdmin):
    list_display = ['title', 'course_offering', 'created', 'deadline_at']
    list_filter = ['course_offering']
    form = AssignmentAdminForm

    def get_readonly_fields(self, request, obj=None):
        return ['course_offering'] if obj else []

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'course_offering':
            kwargs['queryset'] = (CourseOffering.objects
                .select_related("course", "semester"))
        return (super(AssignmentAdmin, self)
                .formfield_for_foreignkey(db_field, request, **kwargs))

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "notify_teachers":
            qs = (CourseOfferingTeacher.objects.select_related(
                "teacher",
                "course_offering"))
            try:
                assignment_pk = request.resolver_match.args[0]
                a = (Assignment.objects
                        .prefetch_related("course_offering__courseofferingteacher_set")
                        .get(pk=assignment_pk))
                teachers = [t.pk for t in a.course_offering.teachers.all()]
                qs = qs.filter(teacher__in=teachers, course_offering=a.course_offering)
            except IndexError:
                pass
            kwargs["queryset"] = qs.order_by("course_offering_id").distinct()
        return super(AssignmentAdmin, self).formfield_for_manytomany(
            db_field, request, **kwargs)

    def save_related(self, request, form, formsets, change):
        if not change and not form.cleaned_data['notify_teachers']:
            co_teachers = form.cleaned_data['course_offering'].courseofferingteacher_set.all()
            form.cleaned_data['notify_teachers'] = [t.pk for t in co_teachers if t.notify_by_default]
        return super(AssignmentAdmin, self).save_related(request, form, formsets, change)


class AssignmentCommentAdmin(RelatedSpecMixin,
                             UbereditorMixin,
                             admin.ModelAdmin):
    readonly_fields = ['student_assignment']
    related_spec = {'select': [('student_assignment',
                                [('assignment',
                                  [('course_offering',
                                    ['semester', 'course'])]),
                                 'student'])]}


class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course_offering', 'grade', 'grade_changed']
    list_filter = ['course_offering__semester', 'course_offering__course']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['student', 'course_offering', 'grade_changed', 'modified']
        else:
            return ['grade_changed', 'modified']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'student':
            kwargs['queryset'] = (get_user_model().objects
                                  .filter(groups__in=[
                                        PARTICIPANT_GROUPS.STUDENT_CENTER,
                                        PARTICIPANT_GROUPS.VOLUNTEER]))
        return (super(EnrollmentAdmin, self)
                .formfield_for_foreignkey(db_field, request, **kwargs))


class StudentAssignmentAdmin(RelatedSpecMixin,
                             admin.ModelAdmin):
    list_display = ['student', 'assignment', 'grade', 'grade_changed', 'state']
    related_spec = {'select': [('assignment',
                                [('course_offering', ['semester', 'course'])]),
                               'student']}

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['student', 'assignment', 'grade_changed', 'state']
        else:
            return ['grade_changed', 'state']


class NonCourseEventAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    list_filter = ['venue']
    list_display = ['name', 'date', 'venue']


class StudentProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'project_type', 'semester']
    list_filter = ['semester']


class OnlineCourseAdmin(UbereditorMixin, admin.ModelAdmin):
    pass


class InternationalSchoolAdmin(UbereditorMixin, admin.ModelAdmin):
    list_display = ['name', 'deadline', 'has_grants']

class UsefulAdmin(admin.ModelAdmin):
    list_filter = ['site']
    list_display = ['question', 'sort']


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
admin.site.register(AssignmentAttachment)
admin.site.register(StudentAssignment, StudentAssignmentAdmin)
admin.site.register(AssignmentComment, AssignmentCommentAdmin)
admin.site.register(Enrollment, EnrollmentAdmin)
admin.site.register(NonCourseEvent, NonCourseEventAdmin)
admin.site.register(StudentProject, StudentProjectAdmin)
admin.site.register(Useful, UsefulAdmin)
