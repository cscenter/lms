# -*- coding: utf-8 -*-

from collections import OrderedDict
from decimal import Decimal

from import_export import resources, fields, widgets
from import_export.instance_loaders import CachedInstanceLoader
from import_export.widgets import IntegerWidget

from admission.constants import ChallengeStatuses
from admission.models import Test, Exam


# XXX: Not tested with django-import-export==1.0.1


class JsonFieldWidget(widgets.Widget):
    # TODO: Maybe should check str type here and parse it to dict
    def clean(self, value, row=None, *args, **kwargs):
        return super(JsonFieldWidget, self).clean(value)

    def render(self, value, obj=None):
        if value:
            return "\n".join("{}: {}".format(k, v) for k, v in value.items())
        return ""


class ContestDetailsMixin:
    # Other fields will be aggregated for the `details` json field
    known_fields = (
        'created',
        'applicant',
        'yandex_login',
        'score',
        'status',
    )

    def before_import(self, data, using_transactions, dry_run, **kwargs):
        if "details" in data.headers:
            print("Column `details` will be replaced")
            del data["details"]
        data.append_col(self.row_collect_details(data.headers),
                        header="details")

    def before_import_row(self, row, **kwargs):
        for k, v in row.items():
            if v == "None":
                row[k] = ""
        super().before_import_row(row, **kwargs)

    def row_collect_details(self, headers):
        """Collect data for `details` column"""
        def wrapper(row):
            details = OrderedDict()
            for i, h in enumerate(headers):
                if h not in self.known_fields:
                    details[h] = row[i]
            return details
        return wrapper


class OnlineTestRecordResource(ContestDetailsMixin,
                               resources.ModelResource):
    applicant = fields.Field(
        column_name='applicant',
        attribute='applicant_id',
        widget=IntegerWidget())
    details = fields.Field(column_name='details',
                           attribute='details',
                           widget=JsonFieldWidget())
    # Note: It returns __str__ representation of `applicant` attribute
    fio = fields.Field(column_name='fio', attribute='applicant')
    yandex_login = fields.Field(column_name='yandex_login',
                                attribute='applicant__yandex_id')
    status = fields.Field(column_name='status', attribute='status',
                          default=ChallengeStatuses.MANUAL)

    class Meta:
        model = Test
        import_id_fields = ('applicant',)
        skip_unchanged = True

    def skip_row(self, instance, original):
        # Leave the lowest score
        if original.score and instance.score:
            return instance.score > original.score
        return super().skip_row(instance, original)


# FIXME: RowResult.obj_repr calls Exam.__str__ which makes additional db hits
class ExamRecordResource(ContestDetailsMixin,
                         resources.ModelResource):
    applicant = fields.Field(
        column_name='applicant',
        attribute='applicant_id',
        widget=IntegerWidget())

    details = fields.Field(column_name='details',
                           attribute='details',
                           widget=JsonFieldWidget())

    class Meta:
        model = Exam
        import_id_fields = ('applicant',)
        skip_unchanged = True
        fields = ('applicant', 'score', 'status', 'details')
        instance_loader_class = CachedInstanceLoader

    def before_import_row(self, row, **kwargs):
        """Double check that score is always a valid type, on DB level we 
        can have null value, so if we omit django field validation on client, 
        it will be very bad"""
        assert int(Decimal(row["score"])) >= 0
