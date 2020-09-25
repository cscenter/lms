from django.contrib import admin

from contests.models import CheckingSystem, Submission, Checker


class CheckingSystemAdmin(admin.ModelAdmin):
    model = CheckingSystem


class CheckerAdmin(admin.ModelAdmin):
    model = Checker


class SubmissionAdmin(admin.ModelAdmin):
    model = Submission


admin.site.register(CheckingSystem, CheckingSystemAdmin)
admin.site.register(Checker, CheckerAdmin)
admin.site.register(Submission, SubmissionAdmin)