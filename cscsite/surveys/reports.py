from collections import defaultdict, Counter
from datetime import datetime
from itertools import groupby
from operator import attrgetter
from typing import NamedTuple

from django.db.models import Prefetch, Count
from django.utils import formats

from core.reports import ReportFileOutput
from surveys.constants import FieldType, CHOICE_FIELD_TYPES
from surveys.models import CourseSurvey, Field, FieldChoice, FieldEntry


class SurveySubmissionsReport(ReportFileOutput):
    def __init__(self, survey: CourseSurvey):
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
        return f"survey_{co.city_id}_{co.meta_course.slug}_{co.semester.slug}_{today}"


class PollOptionResult(NamedTuple):
    value: str
    answers: int
    total: int

    @property
    def percentage(self):
        if self.total:
            return "%.0f" % (100.0 * self.answers / self.total)
        return 0


class SurveySubmissionsStats:
    def __init__(self, survey: CourseSurvey):
        self.survey = survey
        p = Prefetch("choices", queryset=FieldChoice.objects.order_by("order"))
        fields = (Field.objects
                  .filter(form_id=survey.form_id)
                  .order_by("order")
                  .prefetch_related(p))
        self.db_fields = {f.pk: f for f in fields.all()}

    def calculate(self):
        total_submissions = self.survey.form.submissions.count()
        # Count unique submissions per field
        q = (
            FieldEntry.objects
            .filter(form_id=self.survey.form_id)
            .values('field_id')
            .annotate(num_answers=Count('submission_id', distinct=True))
        )
        answers_per_field = {f['field_id']: f['num_answers'] for f in q}
        # Initialize field_stats dict

        def field_stats_factory(field: Field):
            if field.field_type in CHOICE_FIELD_TYPES:
                return {"choices": Counter(), "notes": []}
            return []

        field_stats = {f: field_stats_factory(f) for f in
                       self.db_fields.values()}

        form_entries = self.survey.form.entries.order_by("submission_id")
        grouped_by_submission = groupby(form_entries.iterator(),
                                        key=attrgetter("submission_id"))
        for submission_id, submission_entries in grouped_by_submission:
            field_entries = defaultdict(list)
            for e in submission_entries:
                field_entries[e.field_id].append(e)
            for entries in field_entries.values():
                for entry in entries:
                    db_field = self.db_fields[entry.field_id]
                    if db_field.field_type in [FieldType.TEXT,
                                               FieldType.TEXTAREA]:
                        field_stats[db_field].append(entry.value)
                    elif db_field.field_type in CHOICE_FIELD_TYPES:
                        stats = field_stats[db_field]
                        if entry.is_choice:
                            stats["choices"].update((entry.value,))
                        else:
                            fcd = db_field.field_choices_dict
                            choices = ", ".join(fcd[e.value] for
                                                e in entries if e.is_choice)
                            stats["notes"].append((entry.value, choices))
                    else:
                        raise ValueError(f"Field type {db_field.field_type} is "
                                         f"not supported")

        # Show options starting with the most popular
        for db_field, stats in field_stats.items():
            if db_field.field_type in CHOICE_FIELD_TYPES:
                new_values = []
                selected_options = set()
                # Total answers for the question
                total = answers_per_field.get(db_field.pk, 0)
                choices_stats = stats.get("choices", Counter())
                for value, answers in choices_stats.most_common():
                    selected_options.add(value)
                    label = db_field.field_choices_dict[value]
                    new_option = PollOptionResult(label, answers, total)
                    new_values.append(new_option)
                # Append non-selected options
                for value, label in db_field.field_choices:
                    if value not in selected_options:
                        new_values.append(PollOptionResult(label, 0, total))
                field_stats[db_field]["choices"] = new_values
        return {
            "total_submissions": total_submissions,
            "fields": field_stats
        }

