from __future__ import unicode_literals, absolute_import

from django.contrib import admin
from import_export.admin import ExportActionModelAdmin, ExportMixin

from learning.admission.import_export import ApplicantRecordResource, \
    OnlineTestRecordResource, ExamRecordResource
from learning.admission.models import Campaign, Interview, Applicant, Test, Exam, \
    Interviewer, Comment


class OnlineTestAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = OnlineTestRecordResource
    list_display = ['__str__', 'score']

    def get_queryset(self, request):
        qs = super(OnlineTestAdmin, self).get_queryset(request)
        return qs.select_related('applicant')


class ExamAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = ExamRecordResource
    list_display = ['__str__', 'score']

    def get_queryset(self, request):
        qs = super(ExamAdmin, self).get_queryset(request)
        return qs.select_related('applicant')


class ApplicantRecordResourceAdmin(ExportActionModelAdmin):
    resource_class = ApplicantRecordResource
    list_display = ['id', 'yandex_id', 'second_name', 'first_name', 'last_name', 'campaign']
    list_filter = ['campaign',]
    search_fields = ['yandex_id', 'stepic_id']

admin.site.register(Campaign)
admin.site.register(Applicant, ApplicantRecordResourceAdmin)
admin.site.register(Test, OnlineTestAdmin)
admin.site.register(Exam, ExamAdmin)
admin.site.register(Interviewer)
admin.site.register(Interview)
admin.site.register(Comment)
