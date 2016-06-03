from __future__ import unicode_literals, absolute_import

from jsonfield import JSONField
from prettyjson import PrettyJSONWidget
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from import_export.admin import ExportActionModelAdmin, ExportMixin

from learning.admission.import_export import ApplicantRecordResource, \
    OnlineTestRecordResource, ExamRecordResource
from learning.admission.models import Campaign, Interview, Applicant, Test, \
    Exam, Comment, InterviewAssignment, Contest


class OnlineTestAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = OnlineTestRecordResource
    list_display = ['__str__', 'score']
    list_filter = ['applicant__campaign']
    search_fields = ['applicant__yandex_id', 'applicant__second_name',
                     'applicant__first_name']
    formfield_overrides = {
        JSONField: {'widget': PrettyJSONWidget}
    }

    def get_queryset(self, request):
        qs = super(OnlineTestAdmin, self).get_queryset(request)
        return qs.select_related('applicant')

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'applicant':
            kwargs['queryset'] = (
                Applicant.objects
                         .select_related("campaign",)
                         .order_by("second_name"))
        return (super(OnlineTestAdmin, self)
                .formfield_for_foreignkey(db_field, request, **kwargs))


class ExamAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = ExamRecordResource
    list_display = ['__str__', 'score', 'yandex_contest_id']
    search_fields = ['applicant__yandex_id', 'applicant__second_name',
                     'applicant__first_name']
    list_filter = ['applicant__campaign']
    formfield_overrides = {
        JSONField: {'widget': PrettyJSONWidget}
    }

    def get_queryset(self, request):
        qs = super(ExamAdmin, self).get_queryset(request)
        return qs.select_related('applicant')

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'applicant':
            kwargs['queryset'] = (
                Applicant.objects
                         .select_related("campaign",)
                         .order_by("second_name"))
        return (super(ExamAdmin, self)
                .formfield_for_foreignkey(db_field, request, **kwargs))


class ApplicantRecordResourceAdmin(ExportActionModelAdmin):
    resource_class = ApplicantRecordResource
    list_display = ['id', 'yandex_id', 'second_name', 'first_name', 'last_name',
                    'campaign']
    list_filter = ['campaign', 'status']
    search_fields = ['yandex_id', 'yandex_id_normalize', 'stepic_id',
                     'first_name', 'second_name', 'email']
    readonly_fields = ['yandex_id_normalize']


class ContestAdmin(admin.ModelAdmin):
    list_display = ['contest_id', 'campaign']
    list_filter = ['campaign']


class InterviewAdmin(admin.ModelAdmin):
    list_display = ['date', 'applicant', 'status']
    list_filter = ['status', 'applicant__campaign']

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'applicant':
            kwargs['queryset'] = (
                Applicant.objects
                         .select_related("campaign",)
                         .order_by("second_name"))
        return (super(InterviewAdmin, self)
                .formfield_for_foreignkey(db_field, request, **kwargs))


class InterviewCommentAdmin(admin.ModelAdmin):
    list_display = ['get_interview', 'get_interviewer', 'score']
    search_fields = ['interview__applicant__second_name']
    list_filter = ['interview__applicant__campaign']

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'interview':
            kwargs['queryset'] = (
                Interview.objects.select_related("applicant",
                                                 "applicant__campaign", ))
        if db_field.name == 'get_interview':
            print("test")
        return (super(InterviewCommentAdmin, self)
                .formfield_for_foreignkey(db_field, request, **kwargs))

    def get_queryset(self, request):
        q = super(InterviewCommentAdmin, self).get_queryset(request)
        q = q.select_related("interview__applicant",
                             "interviewer")
        return q

    def get_interview(self, obj):
        return obj.interview.applicant.get_full_name()
    get_interview.short_description = _("Interview")
    get_interview.admin_order_field = "interview__applicant__second_name"

    def get_interviewer(self, obj):
        return obj.interviewer.get_full_name()
    get_interviewer.short_description = _("Interviewer")


admin.site.register(Campaign)
admin.site.register(Applicant, ApplicantRecordResourceAdmin)
admin.site.register(Test, OnlineTestAdmin)
admin.site.register(Exam, ExamAdmin)
admin.site.register(Interview, InterviewAdmin)
admin.site.register(InterviewAssignment)
admin.site.register(Contest, ContestAdmin)
admin.site.register(Comment, InterviewCommentAdmin)
