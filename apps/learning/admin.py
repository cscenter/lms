from django.conf import settings
from django.contrib import admin
from django.db import models as db_models
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from core.admin import BaseModelAdmin, meta
from core.filters import AdminRelatedDropdownFilter
from core.utils import admin_datetime
from core.widgets import AdminRichTextAreaWidget
from courses.models import StudentGroupTypes
from learning.models import GraduateProfile, Invitation, CourseInvitation, \
    StudentAssignment, StudentGroup
from users.models import StudentStatusLog
from .models import AssignmentComment, Enrollment, Event, Useful
from .services import StudentGroupService
from .settings import StudentStatuses


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
            student = instance.student
            if course.group_mode == StudentGroupTypes.BRANCH:
                student_group = StudentGroupService.resolve(course, student,
                                                            settings.SITE_ID)
                if student_group is None:
                    student_group, _ = StudentGroup.objects.get_or_create(
                        course=course,
                        type=StudentGroupTypes.MANUAL,
                        branch_id__isnull=True,
                        name_en="Others",
                        defaults={"name_ru": "Другие"})
                instance.student_group = student_group
        return instance


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
    raw_id_fields = ["assignment", "student"]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['student', 'assignment', 'score_changed', 'state_display']
        else:
            return ['score_changed', 'state_display']


class EventAdmin(BaseModelAdmin):
    list_select_related = ('venue',)
    date_hierarchy = 'date'
    list_filter = ['branch']
    list_display = ['name', 'date', 'venue']


class UsefulAdmin(BaseModelAdmin):
    list_filter = ['site']
    list_display = ['question', 'sort']


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

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if "is_active" in form.changed_data:
            is_active = form.cleaned_data['is_active']
            student_profile = obj.student_profile
            if is_active and student_profile.status != StudentStatuses.GRADUATE:
                student_profile.status = StudentStatuses.GRADUATE
                student_profile.save(update_fields=['status'])
                log_entry = StudentStatusLog(status=StudentStatuses.GRADUATE,
                                             student_profile=student_profile,
                                             entry_author=request.user)
                log_entry.save()


class CourseInlineAdmin(admin.TabularInline):
    model = CourseInvitation
    readonly_fields = ('token', )
    raw_id_fields = ('course',)
    extra = 0


class InvitationAdmin(BaseModelAdmin):
    list_display = ('name', 'semester', 'get_link')
    inlines = (CourseInlineAdmin, )
    list_filter = ('branch', 'semester')
    readonly_fields = ('token',)
    exclude = ('courses',)

    @meta(_("Invitation Link"))
    def get_link(self, obj):
        url = obj.get_absolute_url()
        return mark_safe(f"<a target='_blank' href='{url}'>Смотреть на сайте</a>")


admin.site.register(AssignmentComment, AssignmentCommentAdmin)
admin.site.register(Enrollment, EnrollmentAdmin)
admin.site.register(Invitation, InvitationAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Useful, UsefulAdmin)
admin.site.register(GraduateProfile, GraduateProfileAdmin)
