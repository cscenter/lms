# -*- coding: utf-8 -*-

import datetime
from collections import OrderedDict
from copy import copy

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch
from django.utils import formats
from django.utils.encoding import force_str
from django.utils.numberformat import format
from pandas import DataFrame

from admission.models import Applicant, Interview, Comment, Exam
from core.reports import ReportFileOutput
from core.urls import reverse


class AdmissionApplicantsReport(ReportFileOutput):
    def __init__(self, campaign):
        super().__init__()
        self.campaign = campaign
        self.process()

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

    def process(self):
        # Collect headers
        exclude_applicant_fields = {
            'modified',
            'uuid',
            'yandex_login_q',
            'campaign',
            'user'
        }
        applicant_fields = [f for f in Applicant._meta.fields if
                            f.name not in exclude_applicant_fields]
        self.headers = [force_str(f.verbose_name) for f in applicant_fields]
        self.headers.extend([
            "Результаты теста",
            "Результаты экзамена",
            "Результаты интервью",
            "Комментарии",
        ])
        interviewers = OrderedDict()
        applicants = self.get_queryset()
        # TODO: replace with additional query with LEFT JOIN and campaign_id condition
        for applicant in applicants:
            if hasattr(applicant, "interview"):
                for comment in applicant.interview.comments.all():
                    user = comment.interviewer
                    if user.pk not in interviewers:
                        interviewers[user.pk] = user.get_full_name()
        for pk, full_name in interviewers.items():
            self.headers.append('{}, балл'.format(full_name))
        interviewers_keys = list(interviewers.keys())

        # Collect data
        for applicant in applicants:
            row = []
            for field in applicant_fields:
                value = getattr(applicant, field.name)
                if field.name == 'status':
                    value = applicant.get_status_display()
                elif field.name == 'level_of_education':
                    value = applicant.get_level_of_education_display()
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

            self.data.append([force_str(x) if x is not None else "" for x in
                              row])

    def export_row(self, row):
        return row

    def get_filename(self):
        today = datetime.datetime.now()
        return "admission_{}_{}_report_{}".format(
            self.campaign.branch.code,
            self.campaign.year,
            formats.date_format(today, "SHORT_DATE_FORMAT")
        )


class AdmissionExamReport:
    def __init__(self, campaign):
        self.campaign = campaign

    def generate(self) -> DataFrame:
        headers = [
            "ID",
            "Фамилия",
            "Имя",
            "Отчество",
            "Яндекс.Логин",
            "Статус",
            "Participant ID",
            "Contest ID",
            "Итого"
        ]
        queryset = self.get_queryset()
        tasks_len = 0
        for exam in queryset:
            if exam.details and 'scores' in exam.details:
                tasks_len = max(tasks_len, len(exam.details['scores']))
        headers.extend(f'Задача {i}' for i in range(1, tasks_len + 1))
        data = []
        for i, exam in enumerate(queryset):
            if exam.contest_participant_id:
                participant_id = str(exam.contest_participant_id)
            else:
                participant_id = ""
            row = [
                exam.applicant.pk,
                exam.applicant.surname,
                exam.applicant.first_name,
                exam.applicant.patronymic,
                exam.applicant.yandex_login,
                exam.status,
                participant_id,
                exam.yandex_contest_id,
                exam.score_display()
            ]
            has_any_score = exam.score is not None
            if has_any_score and exam.details and 'scores' in exam.details:
                for s in exam.details['scores']:
                    row.append(str(s))
            else:
                for _ in range(tasks_len):
                    row.append('')
            assert len(row) == len(headers)
            data.append(row)
        return DataFrame.from_records(columns=headers, data=data)

    def get_queryset(self):
        return (Exam.objects
                .filter(applicant__campaign=self.campaign)
                .select_related("applicant")
                .order_by('pk'))

    def get_filename(self):
        today = datetime.datetime.now()
        return "admission_{}_{}_exam_report_{}".format(
            self.campaign.year,
            self.campaign.branch.code,
            formats.date_format(today, "SHORT_DATE_FORMAT")
        )
