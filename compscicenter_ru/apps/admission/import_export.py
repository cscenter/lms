# -*- coding: utf-8 -*-

from collections import OrderedDict
from decimal import Decimal

from import_export import resources, fields, widgets

from admission.models import Applicant, Test, Exam


# XXX: Not tested with django-import-export==1.0.1


class JsonFieldWidget(widgets.Widget):
    # TODO: Maybe should check str type here and parse it to dict
    def clean(self, value, row=None, *args, **kwargs):
        return super(JsonFieldWidget, self).clean(value)

    def render(self, value, obj=None):
        return "\n".join("{}: {}".format(k, v) for k, v in value.items())


class DetailsApplicantImportMixin(object):
    def before_import(self, data, using_transactions, dry_run, **kwargs):
        if "details" in data.headers:
            print("Column `details` will be ignored")
            del data["details"]
        data.append_col(self.row_collect_details(data.headers),
                        header="details")

        if "applicant" not in data.headers:
            data.append_col(self.get_applicant_for_row(data.headers),
                            header="applicant")
        # Optionally save contest id
        if self.contest_id:
            try:
                del data['yandex_contest_id']
            except KeyError:
                pass
            data.append_col(lambda r: self.contest_id,
                            header="yandex_contest_id")

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
                if h not in self.separated_fields:
                    details[h] = row[i]
            return details
        return wrapper

    def get_applicant_for_row(self, headers):
        """Get applicant id by `lookup` field value within provided campaigns"""
        lookup_field = self.lookup_field
        campaign_ids = self.campaign_ids
        lookup_index = headers.index(lookup_field)
        username_index = headers.index("user_name")

        def wrapper(row):
            qs = Applicant.objects.filter(campaign_id__in=campaign_ids)
            if not row[lookup_index]:
                print("Empty {}. Skip".format(lookup_field))
                return ""
            if lookup_field == "yandex_id":
                row[lookup_index] = row[lookup_index].lower().replace("-", ".")
                qs = qs.filter(yandex_id_normalize=row[lookup_index])
            else:
                qs = qs.filter(stepic_id=row[lookup_index])
            cnt = qs.count()
            if cnt > 1:
                print("Duplicates for {} = {}. Skip".format(
                    lookup_field, row[lookup_index]))
                return ""
            elif cnt == 0:
                score_index = headers.index("score")
                print("No applicant for {} = {}; user_name = {}; score = {}; "
                      "contest = {}".format(lookup_field,
                                            row[lookup_index],
                                            row[username_index],
                                            row[score_index],
                                            self.contest_id))
                return ""
            return qs.get().pk

        return wrapper

    def import_field(self, field, obj, data):
        """Don't assign null value for applicant because this field is required, 
        later we skip rows without applicant value"""
        if (field.attribute and
                field.column_name in data and
                field.column_name == "applicant" and
                not data["applicant"]):
            return
        super().import_field(field, obj, data)


class OnlineTestRecordResource(DetailsApplicantImportMixin,
                               resources.ModelResource):
    details = fields.Field(column_name='details',
                           attribute='details',
                           widget=JsonFieldWidget())
    # Note: It returns __str__ representation of `applicant` attribute
    fio = fields.Field(column_name='fio', attribute='applicant')
    yandex_login = fields.Field(column_name='yandex_login',
                                attribute='applicant__yandex_id')

    class Meta:
        model = Test
        import_id_fields = ['applicant']
        skip_unchanged = True

    def __init__(self, **kwargs):
        self.lookup_field = kwargs.get("lookup_field", "")
        self.separated_fields = kwargs.get("separated_fields", False)
        self.campaign_ids = kwargs.get("campaign_ids", False)
        self.contest_id = kwargs.get("contest_id", False)

    def skip_row(self, instance, original):
        # We didn't find applicant, skip record
        if not hasattr(instance, "applicant") or not instance.applicant:
            return True
        # Create record if new
        if not instance.pk:
            return False
        # Otherwise leave the lowest score
        if original.score and instance.score:
            return instance.score > original.score
        return super().skip_row(instance, original)


class ExamRecordResource(DetailsApplicantImportMixin,
                         resources.ModelResource):
    details = fields.Field(column_name='details',
                           attribute='details',
                           widget=JsonFieldWidget())
    # Note: It returns __str__ representation of `applicant` attribute
    fio = fields.Field(column_name='fio', attribute='applicant')
    yandex_login = fields.Field(column_name='yandex_login',
                                attribute='applicant__yandex_id')

    class Meta:
        model = Exam
        import_id_fields = ['applicant']
        skip_unchanged = True

    def __init__(self, **kwargs):
        self.lookup_field = kwargs.get("lookup_field", "")
        self.separated_fields = kwargs.get("separated_fields", False)
        self.campaign_ids = kwargs.get("campaign_ids", False)
        self.contest_id = kwargs.get("contest_id", False)

    def skip_row(self, instance, original):
        # Skip new instances. We only update existed.
        if not instance.pk:
            return True
        if original.yandex_contest_id != str(instance.yandex_contest_id):
            print("Contest id from DB != contest_id from csv for record: "
                  "{}".format(instance.applicant.yandex_id))
            return True
        return False

    def before_import_row(self, row, **kwargs):
        """Double check that score is always a valid type, on DB level we 
        can have null value, so if we omit django field validation on client, 
        it will be very bad"""
        assert int(Decimal(row["score"])) >= 0
