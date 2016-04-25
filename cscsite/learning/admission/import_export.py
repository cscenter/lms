# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

from collections import OrderedDict

from django.utils.encoding import smart_text, force_text
from import_export import resources, fields, widgets
from import_export.instance_loaders import ModelInstanceLoader

from learning.admission.models import Applicant, Test, Exam


class JsonFieldWidget(widgets.Widget):
    # TODO: Maybe should check str type here and parse it to dict
    def clean(self, value):
        return super(JsonFieldWidget, self).clean(value)

    def render(self, value):
        return "\n".join("{}: {}".format(k, v) for k, v in value.items())


class ApplicantRecordResource(resources.ModelResource):
    class Meta:
        model = Applicant
        import_id_fields = ['uuid']
        skip_unchanged = True
        # FIXME: Too slow, looking for another solution
        online_test_fields = ["online_test__" + f.name for f in
                              Test._meta.fields if f.name != 'id']
        exam_fields = ["exam__" + f.name for f in
                       Exam._meta.fields if f.name != 'id']
        fields = [f.name for f in Applicant._meta.fields] + online_test_fields + exam_fields

    def import_field(self, field, obj, data):
        if field.attribute and field.column_name in data:
            if field.column_name == "where_did_you_learn":
                data[field.column_name] = data[field.column_name].strip()
                if not data[field.column_name]:
                    data[field.column_name] = "<не указано>"
            if data[field.column_name] == "None":
                data[field.column_name] = ""
            field.save(obj, data)

    def before_save_instance(self, instance, dry_run):
        """Invoke clean method to normalize yandex_id"""
        instance.clean()


class DetailsApplicantImportMixin(object):
    def before_import(self, data, dry_run, **kwargs):
        if "details" in data.headers:
            print("Column `details` will be ignored")
            del data["details"]
        data.append_col(self.row_collect_details(data.headers),
                        header="details")

        if "applicant" not in data.headers:
            data.append_col(self.row_attach_applicant(data.headers),
                            header="applicant")
        # Optionally save contest id for debug purpose
        # Note: Should implicitly override `yandex_contest_id` field
        if self.contest_id:
            data.append_col(lambda r: self.contest_id,
                            header="yandex_contest_id")

    def import_field(self, field, obj, data):
        if field.attribute and field.column_name in data:
            if data[field.column_name] == "None":
                data[field.column_name] = ""
            # Note: skip save method for `applicant` with null value. Later we skip this row.
            if field.column_name == "applicant" and not data[field.column_name]:
                return
            field.save(obj, data)

    def skip_row(self, instance, original):
        # We can't find applicant by lookup field, so skip record
        if not hasattr(instance, "applicant"):
            return True
        # Skip results with zero score and empty `details`.
        # It means applicant don't even try to pass this contest
        if not instance.score and not any(instance.details.values()):
            return True
        # Otherwise, save lowest score
        if original.pk and original.score < instance.score:
            return True
        return super(DetailsApplicantImportMixin, self).skip_row(instance, original)

    def row_collect_details(self, headers):
        """Collect data for `details` column"""

        def wrapper(row):
            details = OrderedDict()
            for i, h in enumerate(headers):
                if h not in self.allowed_fields:
                    details[h] = row[i]
            return details

        return wrapper

    def row_attach_applicant(self, headers):
        """Get applicant id by `lookup` field and campaign id"""
        lookup_field = self.lookup_field
        campaign_id = self.campaign_id

        def wrapper(row):
            qs = Applicant.objects.filter(campaign_id=campaign_id)
            index = headers.index(lookup_field)
            if not row[index]:
                print("Empty {}. Skip".format(lookup_field))
                return ""
            if lookup_field == "yandex_id":
                row[index] = row[index].lower().replace("-", ".")
                qs = qs.filter(yandex_id_normalize=row[index])
            else:
                qs = qs.filter(stepic_id=row[index])
            cnt = qs.count()
            if cnt > 1:
                print("Duplicates for {}={}. Skip".format(
                    lookup_field, row[index]))
                return ""
            elif cnt == 0:
                try:
                    user_name_index = headers.index("user_name")
                    user_name = row[user_name_index]
                except ValueError:
                    user_name = "-"
                score_index = headers.index("score")
                print("No applicant for {} = {}; user_name = {}; "
                      "score = {}; contest = {}".format(
                    lookup_field, row[index], user_name, row[score_index],
                    self.contest_id))
                return ""
            return qs.get().pk

        return wrapper

    def before_save_instance(self, instance, dry_run):
        # Set default values if not specified
        if not instance.score:
            instance.score = 0


class OnlineTestRecordResource(DetailsApplicantImportMixin,
                               resources.ModelResource):
    details = fields.Field(column_name='details',
                           attribute='details',
                           widget=JsonFieldWidget())
    # Note: Should return __str__ representation of applicant attribute
    fio = fields.Field(column_name='fio',
                       attribute='applicant')
    yandex_login = fields.Field(column_name='yandex_login',
                                attribute='applicant__yandex_id')

    def __init__(self, **kwargs):
        self.lookup_field = kwargs.get("lookup_field", "")
        self.allowed_fields = kwargs.get("allowed_fields", False)
        self.campaign_id = kwargs.get("campaign_id", False)
        self.passing_score = kwargs.get("passing_score", False)
        self.contest_id = kwargs.get("contest_id", False)

    class Meta:
        model = Test
        import_id_fields = ['applicant']
        skip_unchanged = True

    def after_save_instance(self, instance, dry_run):
        """Update applicant status if passing_score provided and instance score
        lower than passing_score
        """
        if self.passing_score and instance.score < self.passing_score:
            instance.applicant.status = Applicant.REJECTED_BY_TEST
            instance.applicant.save()


class ExamRecordResource(DetailsApplicantImportMixin,
                         resources.ModelResource):
    details = fields.Field(column_name='details',
                           attribute='details',
                           widget=JsonFieldWidget())
    # Note: Should return __str__ representation of applicant attribute
    fio = fields.Field(column_name='fio',
                       attribute='applicant')
    yandex_login = fields.Field(column_name='yandex_login',
                                attribute='applicant__yandex_id')

    def __init__(self, **kwargs):
        self.lookup_field = kwargs.get("lookup_field", "")
        self.allowed_fields = kwargs.get("allowed_fields", False)
        self.campaign_id = kwargs.get("campaign_id", False)
        self.passing_score = kwargs.get("passing_score", False)
        self.contest_id = kwargs.get("contest_id", False)

    class Meta:
        model = Test
        import_id_fields = ['applicant']
        skip_unchanged = True

    def after_save_instance(self, instance, dry_run):
        """Update applicant status if score lower than passing_score"""
        if self.passing_score and instance.score < self.passing_score:
            instance.applicant.status = Applicant.REJECTED_BY_EXAM
            instance.applicant.save()
