# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime
from django.utils.encoding import force_text

from core.views import ReportFileOutput
from learning.admission.models import Applicant


class AdmissionReport(ReportFileOutput):
    def __init__(self, campaign_pk):
        self.campaign_pk = campaign_pk
        exclude_applicant_fields = [
            'uuid',
            'yandex_id_normalize',
            'campaign',
            'user'
        ]
        applicant_fields = [f for f in Applicant._meta.fields if
                            f.name not in exclude_applicant_fields]
        self.headers = []
        for f in applicant_fields:
            self.headers.append(force_text(f.verbose_name))
        self.data = []

        for applicant in self.get_queryset():
            row = []
            for field in applicant_fields:
                row.append(force_text(getattr(applicant, field.name, "")))
            self.data.append(row)

    def get_queryset(self):
        return (Applicant.objects
                .filter(campaign=self.campaign_pk)
                .select_related("exam", "online_test")
                .order_by('pk'))

    def export_row(self, row):
        return row

    def get_filename(self):
        today = datetime.datetime.now()
        return "admission_campaign_{}_report_{}".format(
            self.campaign_pk,
            today.strftime("%d.%m.%Y"))
