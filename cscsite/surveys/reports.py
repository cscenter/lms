from collections import defaultdict
from datetime import datetime
from itertools import groupby
from operator import attrgetter

from django.db.models import Prefetch
from django.utils import formats

from core.reports import ReportFileOutput
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
