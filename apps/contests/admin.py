from django.contrib import admin

from contests.models import CheckingSystem, Submission


class CheckingSystemAdmin(admin.ModelAdmin):
    model = CheckingSystem


class SubmissionAdmin(admin.ModelAdmin):
    model = Submission


admin.site.register(CheckingSystem, CheckingSystemAdmin)
admin.site.register(Submission, SubmissionAdmin)