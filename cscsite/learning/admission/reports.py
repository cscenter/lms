# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime

from django.db.models import Prefetch
from django.utils.numberformat import format
from django.utils.encoding import force_text

from core.views import ReportFileOutput
from learning.admission.models import Applicant, Interview
from learning.admission.utils import get_best_interview


class AdmissionReport(ReportFileOutput):
    def __init__(self, campaign_pk):
        self.campaign_pk = campaign_pk
        exclude_applicant_fields = [
            'created',
            'modified',
            'uuid',
            'yandex_id_normalize',
            'campaign',
            'user'
        ]
        applicant_fields = [f for f in Applicant._meta.fields if
                            f.name not in exclude_applicant_fields]
        self.headers = [force_text(f.verbose_name) for f in applicant_fields]
        self.headers.extend([
            "Результаты теста",
            "Результаты экзамена",
            "Результаты интервью",
            "Комментарии",
        ])
        self.data = []

        for applicant in self.get_queryset():
            row = []
            for field in applicant_fields:
                value = getattr(applicant, field.name)
                if field.name == 'status':
                    value = applicant.get_status_display()
                row.append(value)
            if hasattr(applicant, "online_test"):
                row.append(applicant.online_test.score)
            else:
                row.append("")
            if hasattr(applicant, "exam"):
                row.append(applicant.exam.score)
            else:
                row.append("")
            best_interview = get_best_interview(applicant)
            if best_interview is None:
                row.append("<нет интервью>")
                row.append("")
            elif best_interview.average_score() is not None:
                formatted = format(best_interview.average_score(), ".", 2)
                row.append(formatted)
                comments = ""
                for comment in best_interview.comments.all():
                    comments = "{0}{1}\r\n\r\n".format(
                        comments,
                        "{} ({}): {}".format(
                            comment.interviewer,
                            comment.score,
                            comment.text
                        )
                    )
                row.append(comments)
            else:
                row.append("-")
            self.data.append([force_text(x) for x in row])

    def get_queryset(self):
        return (Applicant.objects
                .filter(campaign=self.campaign_pk)
                .select_related("exam", "online_test")
                .prefetch_related(
                    Prefetch(
                        "interviews",
                        queryset=Interview.objects.prefetch_related("comments")
                    )
                )
                .order_by('pk'))

    def export_row(self, row):
        return row

    def get_filename(self):
        today = datetime.datetime.now()
        return "admission_campaign_{}_report_{}".format(
            self.campaign_pk,
            today.strftime("%d.%m.%Y"))
