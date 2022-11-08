from modeltranslation.admin import TranslationAdmin

from django.conf import settings
from django.contrib import admin
from django.db import models as db_models
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from core.admin import BaseModelAdmin, meta
from core.filters import AdminRelatedDropdownFilter
from core.utils import admin_datetime
from core.widgets import AdminRichTextAreaWidget
from courses.models import CourseGroupModes, CourseTeacher
from learning.models import (
    AssignmentScoreAuditLog, CourseInvitation, GraduateProfile, Invitation,
    StudentAssignment, StudentGroup, StudentGroupAssignee, EnrollmentGradeLog
)

from .models import AssignmentComment, Enrollment, Event
from .services import StudentGroupService
from .services.enrollment_service import recreate_assignments_for_student, update_enrollment_grade
from .services.personal_assignment_service import update_personal_assignment_score
from .settings import AssignmentScoreUpdateSource, EnrollmentGradeUpdateSource


class CourseTeacherAdmin(BaseModelAdmin):
    list_display = ('teacher', 'course')
    list_select_related = ['course__meta_course', 'course__semester', 'teacher']
    list_filter = [
        ('course__semester', AdminRelatedDropdownFilter)
    ]
    search_fields = ('teacher__last_name', 'course__meta_course__name')
    raw_id_fields = ('course', 'teacher')

    def has_module_permission(self, request) -> bool:
        """Hides module from the index page"""
        return False


class StudentGroupAssigneeInline(admin.TabularInline):
    model = StudentGroupAssignee
    list_display = ('assignee',)
    fields = ('assignee',)
    raw_id_fields = ('assignee',)
    extra = 0


class StudentGroupAdmin(TranslationAdmin, BaseModelAdmin):
    list_display = ('name', 'type', 'course', 'main_branch')
    list_select_related = [
        'course__meta_course',
        'course__semester',
        'course__main_branch__city'
    ]
    list_filter = [
        ('course__semester', AdminRelatedDropdownFilter),
        'course__main_branch'
    ]
    search_fields = ['course__meta_course__name']
    raw_id_fields = ('course', 'invitation')

    inlines = [
        StudentGroupAssigneeInline,
    ]

    @meta(_("Branch"))
    def main_branch(self, obj: StudentGroup):
        return obj.course.main_branch.name


class AssignmentCommentAdmin(BaseModelAdmin):
    list_select_related = [
        'author',
        'student_assignment__student',
        'student_assignment__assignment',
        'student_assignment__assignment__course',
        'student_assignment__assignment__course__semester',
        'student_assignment__assignment__course__meta_course',
    ]
    readonly_fields = ['student_assignment']
    raw_id_fields = ('author',)
    list_display = ["get_assignment_name", "get_student", "author"]
    search_fields = ["student_assignment__assignment__title",
                     "student_assignment__assignment__id"]
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }

    def get_student(self, obj: AssignmentComment):
        return obj.student_assignment.student
    get_student.short_description = _("Assignment|assigned_to")

    def get_assignment_name(self, obj: AssignmentComment):
        return obj.student_assignment.assignment.title
    get_assignment_name.admin_order_field = 'student_assignment__assignment__title'
    get_assignment_name.short_description = _("Asssignment|name")


class EnrollmentGradeLogAdminInline(admin.TabularInline):
    list_select_related = ['student_profile', 'entry_author']
    model = EnrollmentGradeLog
    extra = 0
    show_change_link = True
    readonly_fields = ('grade_changed_at', 'source', 'grade', 'entry_author')
    ordering = ['-grade_changed_at', '-pk']

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class EnrollmentAdmin(BaseModelAdmin):
    list_select_related = ['course', 'course__semester', 'course__meta_course',
                           'course__main_branch', 'student']
    list_display = ['student', 'course', 'is_deleted', 'grade',
                    'grade_changed_local']
    ordering = ['-pk']
    list_filter = [
        'course__main_branch__site',
        'course__main_branch',
        ('course__semester', AdminRelatedDropdownFilter)
    ]
    search_fields = ['course__meta_course__name', 'student__last_name']
    exclude = ['grade_changed']
    raw_id_fields = ("student", "course", "invitation", "student_profile",
                     "student_group")
    inlines = [EnrollmentGradeLogAdminInline]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['course', 'student', 'grade_changed_local', 'modified']
        else:
            return ['grade_changed_local', 'modified']

    def grade_changed_local(self, obj):
        return admin_datetime(obj.grade_changed_local())
    grade_changed_local.admin_order_field = 'grade_changed'
    grade_changed_local.short_description = _("Enrollment|grade changed")

    def save_form(self, request, form, change):
        created = not change
        instance = super().save_form(request, form, change)
        if created:
            course = instance.course
            if course.group_mode != CourseGroupModes.NO_GROUPS:
                student_group = StudentGroupService.resolve(course, student_profile=instance.student_profile)
                instance.student_group = student_group
        return instance

    def save_model(self, request, obj, form, change):
        if change:
            if "grade" in form.changed_data:
                # there is no concurrency check
                update_enrollment_grade(obj,
                                        editor=request.user,
                                        old_grade=Enrollment.objects.get(pk=obj.pk).grade,
                                        new_grade=form.cleaned_data['grade'],
                                        source=EnrollmentGradeUpdateSource.FORM_ADMIN)
        super().save_model(request, obj, form, change)
        if not change:
            recreate_assignments_for_student(obj)


class StudentAssignmentWatcherInlineAdmin(admin.TabularInline):
    verbose_name_plural = _("Watchers")
    verbose_name = _("Watcher")
    model = StudentAssignment.watchers.through
    raw_id_fields = ('user',)
    extra = 0


class AssignmentScoreAuditLogAdminInline(admin.TabularInline):
    model = AssignmentScoreAuditLog
    readonly_fields = ('created_at', 'score_old', 'score_new', 'changed_by', 'source')
    extra = 0
    show_change_link = False
    ordering = ['-created_at']

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('changed_by')


@admin.register(StudentAssignment)
class StudentAssignmentAdmin(BaseModelAdmin):
    list_select_related = [
        'student',
        'assignment',
        'assignment__course',
        'assignment__course__semester',
        'assignment__course__meta_course',
    ]
    list_display = ['student', 'assignment', 'score', 'score_changed',
                    'state_display']
    search_fields = ['student__last_name']
    raw_id_fields = ["assignment", "student", "assignee"]
    exclude = ['watchers']
    inlines = [StudentAssignmentWatcherInlineAdmin, AssignmentScoreAuditLogAdminInline]

    class Media:
        css = {
            'all': ('v2/css/django_admin.css',)
        }

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['student', 'assignment', 'score_changed', 'state_display']
        else:
            return ['score_changed', 'state_display']

    def save_model(self, request, obj, form, change):
        is_score_has_changed = obj.tracker.has_changed('score') or (not change and obj.score is not None)
        score_old = obj.tracker.previous('score')
        # Save object with an old score, then upgrade it with a new score value
        score_new = obj.score
        obj.score = score_old
        super().save_model(request, obj, form, change)
        if is_score_has_changed:
            update_personal_assignment_score(student_assignment=obj,
                                             changed_by=request.user,
                                             score_old=score_old,
                                             score_new=score_new,
                                             source=AssignmentScoreUpdateSource.FORM_ADMIN)


class EventAdmin(BaseModelAdmin):
    list_select_related = ('venue',)
    date_hierarchy = 'date'
    list_filter = ['branch']
    list_display = ['name', 'date', 'venue']


class GraduateProfileAdmin(BaseModelAdmin):
    list_select_related = ('student_profile', 'student_profile__user')
    list_display = ('student_name', 'graduation_year', 'is_active')
    list_filter = ('student_profile__site', 'student_profile__branch',
                   'graduation_year')
    search_fields = ('student_profile__user__last_name',)
    raw_id_fields = ('student_profile',)

    @meta(_("Student"))
    def student_name(self, obj):
        return obj.student_profile.user.get_full_name()


class CourseInlineAdmin(admin.TabularInline):
    model = CourseInvitation
    readonly_fields = ('token', )
    raw_id_fields = ('course',)
    extra = 0


class InvitationAdmin(BaseModelAdmin):
    list_display = ('name', 'branch', 'semester', 'get_link')
    list_select_related = ['branch__site', 'semester']
    inlines = (CourseInlineAdmin, )
    list_filter = [
        'branch__site',
        'branch',
        ('semester', AdminRelatedDropdownFilter),
    ]
    readonly_fields = ('token',)
    exclude = ('courses', 'enrolled_students')

    @meta(_("Invitation Link"))
    def get_link(self, obj):
        url = obj.get_absolute_url()
        return mark_safe(f"<a target='_blank' href='{url}'>Смотреть на сайте</a>")


admin.site.register(CourseTeacher, CourseTeacherAdmin)
admin.site.register(StudentGroup, StudentGroupAdmin)
admin.site.register(AssignmentComment, AssignmentCommentAdmin)
admin.site.register(Enrollment, EnrollmentAdmin)
admin.site.register(Invitation, InvitationAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(GraduateProfile, GraduateProfileAdmin)
