import datetime
from typing import Callable

from pandas import DataFrame

from django.db.models import Prefetch
from django.utils import formats
from django.utils.encoding import force_str

from admission.constants import ApplicantStatuses, InterviewSections
from admission.models import Applicant, Campaign, Comment, Exam, Interview
from core.reports import ReportFileOutput
from core.urls import reverse


class AdmissionApplicantsReport(ReportFileOutput):
    def __init__(self, campaign):
        super().__init__()
        self.campaign = campaign
        self.process()

    def get_queryset(self):
        return (
            Applicant.objects.filter(campaign=self.campaign.pk)
            .select_related("exam", "online_test")
            .prefetch_related(
                "university_legacy",
                Prefetch(
                    "interviews",
                    queryset=(
                        Interview.objects.prefetch_related(
                            Prefetch(
                                "comments",
                                queryset=(
                                    Comment.objects.select_related("interviewer")
                                ),
                            )
                        )
                    ),
                ),
            )
            .order_by("pk")
        )

    def process(self):
        # Collect headers
        exclude_applicant_fields = {
            "modified",
            "uuid",
            "yandex_login_q",
            "campaign",
            "user",
            "meta",
        }
        applicant_fields = [
            f for f in Applicant._meta.fields if f.name not in exclude_applicant_fields
        ]
        self.headers = [force_str(f.verbose_name) for f in applicant_fields]
        self.headers.extend(
            [
                "Результаты теста",
                "Результаты экзамена",
            ]
        )
        applicants = self.get_queryset()
        # Collect data
        for applicant in applicants:
            row = []
            for field in applicant_fields:
                value = getattr(applicant, field.name)
                if field.name == "status":
                    value = applicant.get_status_display()
                elif field.name == "level_of_education":
                    value = applicant.get_level_of_education_display()
                elif field.name == "has_diploma":
                    value = applicant.get_has_diploma_display()
                elif field.name == "gender":
                    value = applicant.get_gender_display()
                elif field.name == "diploma_degree":
                    value = applicant.get_diploma_degree_display()
                elif field.name == "id":
                    value = reverse("admission:applicants:detail", args=[value])
                elif field.name == "created":
                    value = formats.date_format(applicant.created, "SHORT_DATE_FORMAT")
                row.append(value)
            if hasattr(applicant, "online_test"):
                row.append(applicant.online_test.score)
            else:
                row.append("")
            if hasattr(applicant, "exam"):
                row.append(applicant.exam.score)
            else:
                row.append("")
            self.data.append([force_str(x) if x is not None else "" for x in row])

    def export_row(self, row):
        return row

    def get_filename(self):
        today = datetime.datetime.now()
        return "admission_{}_{}_report_{}".format(
            self.campaign.branch.code,
            self.campaign.year,
            formats.date_format(today, "SHORT_DATE_FORMAT"),
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
            "Итого",
        ]
        queryset = self.get_queryset()
        tasks_len = 0
        for exam in queryset:
            if exam.details and "scores" in exam.details:
                tasks_len = max(tasks_len, len(exam.details["scores"]))
        headers.extend(f"Задача {i}" for i in range(1, tasks_len + 1))
        data = []
        for i, exam in enumerate(queryset):
            if exam.contest_participant_id:
                participant_id = str(exam.contest_participant_id)
            else:
                participant_id = ""
            row = [
                exam.applicant.pk,
                exam.applicant.last_name,
                exam.applicant.first_name,
                exam.applicant.patronymic,
                exam.applicant.yandex_login,
                exam.status,
                participant_id,
                exam.yandex_contest_id,
                exam.score_display(),
            ]
            has_any_score = exam.score is not None
            if has_any_score and exam.details and "scores" in exam.details:
                for s in exam.details["scores"]:
                    row.append(str(s))
            else:
                for _ in range(tasks_len):
                    row.append("")
            assert len(row) == len(headers)
            data.append(row)
        return DataFrame.from_records(columns=headers, data=data)

    def get_queryset(self):
        return (
            Exam.objects.filter(applicant__campaign=self.campaign)
            .select_related("applicant")
            .order_by("pk")
        )

    def get_filename(self):
        today = datetime.datetime.now()
        return "admission_{}_{}_exam_report_{}".format(
            self.campaign.year,
            self.campaign.branch.code,
            formats.date_format(today, "SHORT_DATE_FORMAT"),
        )


def generate_admission_interviews_report(
    *, campaign: Campaign, url_builder: Callable[[str], str] = str
) -> DataFrame:
    headers = [
        "Фамилия",
        "Имя",
        "Отчество",
        "Ссылка",
        "Статус анкеты",
    ]
    interview_section_indexes = {}
    for index, (value, label) in enumerate(InterviewSections.choices):
        headers.append(f"{label} / балл")
        headers.append(f"{label} / комментарии")
        interview_section_indexes[value] = 2 * index
    interview_comments = Prefetch(
        "interviews__comments",
        queryset=(Comment.objects.prefetch_related("interviewer")),
    )
    applicants = (
        Applicant.objects.filter(
            campaign=campaign, status__in=ApplicantStatuses.RESULTS_STATUSES
        )
        .order_by("pk")
        .prefetch_related("interviews", interview_comments)
    )
    data = []
    for i, applicant in enumerate(applicants):
        row = [
            applicant.last_name,
            applicant.first_name,
            applicant.patronymic,
            url_builder(applicant.get_absolute_url()),
            applicant.get_status_display(),
        ]
        interview_details = ["" for _ in range(2 * len(InterviewSections.values))]
        for interview in applicant.interviews.all():
            interview_comments = ""
            for c in interview.comments.all():
                author = c.interviewer.get_full_name()
                interview_comments += f"{author}: {c.score}\n{c.text}\n\n"
            index = interview_section_indexes[interview.section]
            interview_details[index] = interview.get_average_score_display()
            interview_details[index + 1] = interview_comments.rstrip()
        row.extend(interview_details)
        assert len(row) == len(headers)
        data.append(row)
    return DataFrame.from_records(columns=headers, data=data)
