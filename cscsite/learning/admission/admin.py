from __future__ import unicode_literals, absolute_import

from django.contrib import admin
from import_export.admin import ImportExportMixin, ImportExportModelAdmin, \
    ExportActionModelAdmin

from learning.admission.import_export import ApplicantRecordResource
from learning.admission.models import Campaign, Interview, Applicant, Test, Exam, \
    Interviewer, Comment

admin.site.register(Campaign)
admin.site.register(Test)
admin.site.register(Exam)
admin.site.register(Interviewer)
admin.site.register(Interview)
admin.site.register(Comment)

class ApplicantRecordResourceAdmin(ExportActionModelAdmin):
    resource_class = ApplicantRecordResource
    list_display = ['id', 'yandex_id', 'second_name', 'first_name', 'last_name', 'campaign']
    list_filter = ['campaign',]
    search_fields = ['yandex_id', 'stepic_id']

admin.site.register(Applicant, ApplicantRecordResourceAdmin)
