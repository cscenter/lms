# -*- coding: utf-8 -*-

import datetime
from collections import OrderedDict

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch
from django.utils import formats
from django.utils.encoding import force_text
from django.utils.numberformat import format

from admission.models import Applicant, Interview, Comment
from core.reports import ReportFileOutput
from core.urls import reverse


class AdmissionReport(ReportFileOutput):
    def __init__(self, campaign):
        self.campaign = campaign
        self.max_interview_comments = 0
        applicant_fields = self.get_applicant_fields()

        self.headers = [force_text(f.verbose_name) for f in applicant_fields]
        self.headers.extend([
            "Результаты теста",
            "Результаты экзамена",
            "Результаты интервью",
            "Комментарии",
        ])
        # Collect interviewers
        interviewers = OrderedDict()
        applicants = self.get_queryset()
        # TODO: replace with additional query with LEFT JOIN and campaign_id condition
        for applicant in applicants:
            if hasattr(applicant, "interview"):
                for comment in applicant.interview.comments.all():
                    user = comment.interviewer
                    if user.pk not in interviewers:
                        interviewers[user.pk] = user.get_full_name()
        interviewers_keys = list(interviewers.keys())
        for pk, full_name in interviewers.items():
            self.headers.append('{}, балл'.format(full_name))
        # TODO: replace with iterator
        self.data = []

        for applicant in applicants:
            row = []
            for field in applicant_fields:
                value = getattr(applicant, field.name)
                if field.name == 'status':
                    value = applicant.get_status_display()
                elif field.name == 'course':
                    value = applicant.get_course_display()
                elif field.name == 'id':
                    value = reverse("admission:applicant_detail", args=[value])
                elif field.name == 'created':
                    value = formats.date_format(applicant.created,
                                                "SHORT_DATE_FORMAT")
                row.append(value)
            if hasattr(applicant, "online_test"):
                row.append(applicant.online_test.score)
            else:
                row.append("")
            if hasattr(applicant, "exam"):
                row.append(applicant.exam.score)
            else:
                row.append("")
            try:
                interview = applicant.interview
                if interview.average_score is not None:
                    formatted = format(interview.average_score, ".", 2)
                    row.append(formatted)
                    # Add interviewers comments and score
                    comments = ""
                    interviewers_columns = [None] * len(interviewers)
                    for comment in interview.comments.all():
                        comments = "{0}{1}\r\n\r\n".format(
                            comments,
                            "{}: {}".format(comment.interviewer, comment.text)
                        )
                        index = interviewers_keys.index(comment.interviewer.pk)
                        interviewers_columns[index] = comment.score
                    row.append(comments)
                    row.extend(interviewers_columns)
                else:
                    row.append("-")
            except ObjectDoesNotExist:
                row.append("<нет интервью>")
                row.append("")

            self.data.append([force_text(x) if x is not None else "" for x in
                              row])

    @staticmethod
    def get_applicant_fields():
        exclude_applicant_fields = {
            'modified',
            'uuid',
            'yandex_id_normalize',
            'campaign',
            'user'
        }
        return [f for f in Applicant._meta.fields if
                f.name not in exclude_applicant_fields]

    def get_queryset(self):
        return (Applicant.objects
                .filter(campaign=self.campaign.pk)
                .select_related("exam", "online_test")
                .prefetch_related(
                    "university",
                    Prefetch(
                        "interview",
                        queryset=(Interview.objects
                                  .prefetch_related(
                                        Prefetch(
                                            "comments",
                                            queryset=(Comment.objects
                                                       .select_related("interviewer"))))
                        )))
                .order_by('pk'))

    def export_row(self, row):
        return row

    def get_filename(self):
        today = datetime.datetime.now()
        return "admission_{}_{}_report_{}".format(
            self.campaign.branch.code,
            self.campaign.year,
            formats.date_format(today, "SHORT_DATE_FORMAT")
        )
