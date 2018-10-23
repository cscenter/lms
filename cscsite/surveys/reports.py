from collections import defaultdict, Counter
from datetime import datetime
from itertools import groupby
from operator import attrgetter
from typing import NamedTuple

from django.db.models import Prefetch
from django.utils import formats

from core.reports import ReportFileOutput
from surveys.constants import FieldType
from surveys.models import CourseOfferingSurvey, Field, FieldChoice


class SurveySubmissionsReport(ReportFileOutput):
    def __init__(self, survey: CourseOfferingSurvey):
        self.survey = survey
        p = Prefetch("choices", queryset=FieldChoice.objects.order_by("order"))
        fields = (Field.objects
                  .filter(form_id=survey.form_id)
                  .order_by("order")
                  .prefetch_related(p))
        self.db_fields = {f.pk: f for f in fields.all()}

    @property
    def headers(self):
        return [f.label for f in self.db_fields.values()]

    def export_row(self, submission):
        return ["\n".join(v) for v in submission]

    @property
    def data(self):
        form_entries = self.survey.form.entries.order_by("submission_id")
        grouped_by_submission = groupby(form_entries.iterator(),
                                        key=attrgetter("submission_id"))
        for submission_id, entries in grouped_by_submission:
            field_entries = defaultdict(list)
            for e in entries:
                field_entries[e.field_id].append(e)
            submission_data = []
            for db_field in self.db_fields.values():
                entries = field_entries[db_field.pk]
                value = db_field.to_export_value(entries)
                submission_data.append(value)

            yield submission_data

    def get_filename(self):
        today = formats.date_format(datetime.now(), "SHORT_DATE_FORMAT")
        co = self.survey.course_offering
        return f"survey_{co.city_id}_{co.course.slug}_{co.semester.slug}_{today}"


class PollOptionResult(NamedTuple):
    value: str
    answers: int
    percentage: str


class SurveySubmissionsStats:
    def __init__(self, survey: CourseOfferingSurvey):
        self.survey = survey
        p = Prefetch("choices", queryset=FieldChoice.objects.order_by("order"))
        fields = (Field.objects
                  .filter(form_id=survey.form_id)
                  .order_by("order")
                  .prefetch_related(p))
        self.db_fields = {f.pk: f for f in fields.all()}

    def calculate(self):
        total_submissions = self.survey.form.submissions.count()
        field_stats = {f: None for f in self.db_fields.values()}
        form_entries = self.survey.form.entries.all()
        for entry in form_entries:
            db_field = self.db_fields[entry.field_id]
            if db_field.field_type in [FieldType.TEXT, FieldType.TEXTAREA]:
                if field_stats[db_field] is None:
                    field_stats[db_field] = []
                field_stats[db_field].append(entry.value)
            elif db_field.field_type == FieldType.RADIO_MULTIPLE:
                if field_stats[db_field] is None:
                    field_stats[db_field] = Counter()
                field_stats[db_field].update((entry.value,))
            elif db_field.field_type == FieldType.CHECKBOX_MULTIPLE:
                pass
            elif db_field.field_type == FieldType.CHECKBOX_MULTIPLE_WITH_NOTE:
                pass
            else:
                raise ValueError(f"Field type {db_field.field_type} is "
                                 f"not supported")

        for db_field, values in field_stats.items():
            if db_field.field_type == FieldType.RADIO_MULTIPLE:
                new_values = []
                selected_options = set()
                for value, answers in values.most_common():
                    selected_options.add(value)
                    label = db_field.field_choices_dict[value]
                    new_option = PollOptionResult(
                        label, answers,
                        '%.2f%%' % (100.0 * answers / total_submissions)
                    )
                    new_values.append(new_option)
                # Append non-selected options
                for value, label in db_field.field_choices:
                    if value not in selected_options:
                        new_values.append(PollOptionResult(label, 0, '0%'))
                field_stats[db_field] = new_values
        return {
            "total_submissions": total_submissions,
            "fields": field_stats
        }

