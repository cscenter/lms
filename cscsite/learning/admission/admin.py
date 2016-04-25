from __future__ import unicode_literals, absolute_import

try:
    import json
except ImportError:
    from django.utils import simplejson as json

from django import forms
from django.contrib import admin
from import_export.admin import ExportActionModelAdmin, ExportMixin

from learning.admission.import_export import ApplicantRecordResource, \
    OnlineTestRecordResource, ExamRecordResource
from learning.admission.models import Campaign, Interview, Applicant, Test, Exam, \
    Interviewer, Comment, InterviewAssignments, Contest
from learning.admission.widgets import SimpleJSONWidget


class OnlineTestAdminForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = "__all__"
        widgets = {
            'details': SimpleJSONWidget,
        }


class OnlineTestAdmin(ExportMixin, admin.ModelAdmin):
    form = OnlineTestAdminForm
    resource_class = OnlineTestRecordResource
    list_display = ['__str__', 'score']
    list_filter = ['applicant__campaign']
    search_fields = ['applicant__yandex_id', 'applicant__second_name', 'applicant__first_name']

    def get_queryset(self, request):
        qs = super(OnlineTestAdmin, self).get_queryset(request)
        return qs.select_related('applicant')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'applicant':
            kwargs['queryset'] = (Applicant.objects.select_related("campaign", ).order_by("second_name"))
        return (super(OnlineTestAdmin, self)
                .formfield_for_foreignkey(db_field, request, **kwargs))


class ExamAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = ExamRecordResource
    list_display = ['__str__', 'score', 'yandex_contest_id']
    search_fields = ['applicant__yandex_id', 'applicant__second_name',
                     'applicant__first_name']

    def get_queryset(self, request):
        qs = super(ExamAdmin, self).get_queryset(request)
        return qs.select_related('applicant')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'applicant':
            kwargs['queryset'] = (
            Applicant.objects.select_related("campaign", ).order_by("second_name"))
        return (super(ExamAdmin, self)
                .formfield_for_foreignkey(db_field, request, **kwargs))


class ApplicantRecordResourceAdmin(ExportActionModelAdmin):
    resource_class = ApplicantRecordResource
    list_display = ['id', 'yandex_id', 'second_name', 'first_name', 'last_name', 'campaign']
    list_filter = ['campaign',]
    search_fields = ['yandex_id', 'yandex_id_normalize', 'stepic_id', 'first_name', 'second_name', 'email']
    readonly_fields = ['yandex_id_normalize']


class InterviewerAdmin(admin.ModelAdmin):
    list_display = ['user', 'campaign']
    list_filter = ['campaign']


class InterviewAdmin(admin.ModelAdmin):
    list_display = ['date', 'applicant']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'applicant':
            kwargs['queryset'] = (Applicant.objects.select_related("campaign",))
        return (super(InterviewAdmin, self)
                .formfield_for_foreignkey(db_field, request, **kwargs))



admin.site.register(Campaign)
admin.site.register(Applicant, ApplicantRecordResourceAdmin)
admin.site.register(Test, OnlineTestAdmin)
admin.site.register(Exam, ExamAdmin)
admin.site.register(Interviewer, InterviewerAdmin)
admin.site.register(Interview, InterviewAdmin)
admin.site.register(InterviewAssignments)
admin.site.register(Contest)
admin.site.register(Comment)
