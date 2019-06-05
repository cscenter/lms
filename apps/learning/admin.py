from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import models as db_models
from django.utils.translation import ugettext_lazy as _

from core.admin import CityAwareModelForm, CityAwareAdminSplitDateTimeWidget, \
    CityAwareSplitDateTimeField, RelatedSpecMixin
from core.filters import AdminRelatedDropdownFilter
from core.utils import admin_datetime
from core.widgets import AdminRichTextAreaWidget
from learning.models import GraduateProfile
from users.constants import AcademicRoles
from .models import AssignmentComment, Enrollment, Event, Useful, Branch


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
                 ('assignment', [('course', ['semester', 'meta_course'])]),
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
    list_display = ['student', 'course', 'is_deleted', 'grade',
                    'grade_changed_local']
    ordering = ['-pk']
    list_filter = [
        'course__city_id',
        ('course__semester', AdminRelatedDropdownFilter)
    ]
    search_fields = ['course__meta_course__name']
    exclude = ['grade_changed']
    raw_id_fields = ["student", "course"]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['student', 'course', 'grade_changed_local', 'modified']
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
                                        AcademicRoles.STUDENT_CENTER,
                                        AcademicRoles.VOLUNTEER]))
        return (super(EnrollmentAdmin, self)
                .formfield_for_foreignkey(db_field, request, **kwargs))


class StudentAssignmentAdmin(RelatedSpecMixin, admin.ModelAdmin):
    list_display = ['student', 'assignment', 'score', 'score_changed', 'state']
    related_spec = {'select': [('assignment',
                                [('course', ['semester', 'meta_course'])]),
                               'student']}
    search_fields = ['student__last_name']
    raw_id_fields = ["assignment", "student"]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['student', 'assignment', 'score_changed', 'state']
        else:
            return ['score_changed', 'state']


class NonCourseEventAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    list_filter = ['venue']
    list_display = ['name', 'date', 'venue']


class UsefulAdmin(admin.ModelAdmin):
    list_filter = ['site']
    list_display = ['question', 'sort']


class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_remote')


class GraduateProfileAdmin(admin.ModelAdmin):
    list_display = ('student', 'graduation_year')
    list_filter = ('graduation_year',)
    raw_id_fields = ('student',)


admin.site.register(AssignmentComment, AssignmentCommentAdmin)
admin.site.register(Enrollment, EnrollmentAdmin)
admin.site.register(Event, NonCourseEventAdmin)
admin.site.register(Useful, UsefulAdmin)
admin.site.register(Branch, BranchAdmin)
admin.site.register(GraduateProfile, GraduateProfileAdmin)
