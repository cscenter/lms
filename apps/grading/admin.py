from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from grading.models import CheckingSystem, Submission, Checker
from core.admin import meta


class CheckingSystemAdmin(admin.ModelAdmin):
    pass


class CheckerAdmin(admin.ModelAdmin):
    pass


class SubmissionAdmin(admin.ModelAdmin):
    list_select_related = [
        'assignment_submission__student_assignment__assignment',
        'assignment_submission__student_assignment__student'
    ]
    search_fields = ['assignment_submission__student_assignment__assignment__title']
    list_display = ['id', 'status', 'assignment_name', 'student_name']
    raw_id_fields = ['assignment_submission']

    @meta(_("Assignment"))
    def assignment_name(self, obj):
        return obj.assignment_submission.student_assignment.assignment.title

    @meta(_("Student"))
    def student_name(self, obj):
        return obj.assignment_submission.student_assignment.student


admin.site.register(CheckingSystem, CheckingSystemAdmin)
admin.site.register(Checker, CheckerAdmin)
admin.site.register(Submission, SubmissionAdmin)
