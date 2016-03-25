# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

from import_export import resources

from learning.admission.models import Applicant, Test


class ApplicantRecordResource(resources.ModelResource):

    class Meta:
        model = Applicant
        import_id_fields = ['uuid']
        skip_unchanged = True

    def import_field(self, field, obj, data):
        if field.attribute and field.column_name in data:
            if data[field.column_name] == "None":
                data[field.column_name] = ""
            field.save(obj, data)


class OnlineTestRecordResource(resources.ModelResource):

    def __init__(self, lookup_field, allowed_fields, campaign_id, passing_score, contest_id):
        self.lookup_field = lookup_field
        self.allowed_fields = allowed_fields
        self.campaign_id = campaign_id
        self.passing_score = passing_score
        self.contest_id = contest_id

    class Meta:
        model = Test
        import_id_fields = ['applicant']
        skip_unchanged = True

    def before_import(self, data, dry_run, **kwargs):
        if "details" in data.headers:
            print("Column `details` will be ignored")
            del data["details"]
        data.append_col(self.row_collect_details(data.headers), header="details")

        if "applicant" not in data.headers:
            data.append_col(self.row_attach_applicant(data.headers),
                            header="applicant")
        # Optionally save contest id for debug purpose
        if self.contest_id:
            data.append_col(lambda r: self.contest_id, header="yandex_contest_id")

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
        if not instance.score and not all(instance.details.values()):
            return True
        # Otherwise, save lowest score
        if original.pk and original.score < instance.score:
            return True
        return super(OnlineTestRecordResource, self).skip_row(instance, original)

    def row_collect_details(self, headers):
        """Collect data for `details` column"""
        def wrapper(row):
            details = {}
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
                qs = qs.filter(yandex_id=row[index])
            else:
                qs = qs.filter(stepic_id=row[index])
            cnt = qs.count()
            if cnt > 1:
                print("Duplicates for {}={}. Skip".format(
                    lookup_field, row[index]))
                return ""
            elif cnt == 0:
                print("No matching applicant for {}={}. Skip".format(
                    lookup_field, row[index]))
                return ""
            return qs.get().pk
        return wrapper

    def before_save_instance(self, instance, dry_run):
        # Set default values if not specified
        if not instance.score:
            instance.score = 0

    def after_save_instance(self, instance, dry_run):
        """Update applicant status if score lower than passing_score"""
        if instance.score < self.passing_score:
            instance.applicant.status = Applicant.REJECTED_BY_TEST
            instance.applicant.save()
