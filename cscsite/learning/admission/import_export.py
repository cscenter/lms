# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

from import_export import resources
from learning.admission.models import Applicant, Test


class ApplicantRecordResource(resources.ModelResource):

    class Meta:
        model = Applicant
        import_id_fields = ['uuid']
        # skip_unchanged = True

    def import_field(self, field, obj, data):
        if field.attribute and field.column_name in data:
            if data[field.column_name] == "None":
                data[field.column_name] = ""
            field.save(obj, data)
    #
    # def before_save_instance(self, instance, dry_run):
    #     # Show error if no campaign specified?
    #     pass


class OnlineTestRecordResource(resources.ModelResource):

    class Meta:
        model = Test
        # import_id_fields = ['uuid']

    def get_instance(self, instance_loader, row):
        """Try to find instance by `applicant` and `campaign` values first, then by uuid"""
        return False

    def import_field(self, field, obj, data):
        if field.attribute and field.column_name in data:
            if data[field.column_name] == "None":
                data[field.column_name] = ""
            # By fact we remove this field
            if field.column_name == "applicant" and not data[field.column_name]:
                return
            field.save(obj, data)

    def skip_row(self, instance, original):
        if not hasattr(instance, "applicant"):
            return True
        skip = super(OnlineTestRecordResource, self).skip_row(instance, original)
        return skip
    #
    # def before_save_instance(self, instance, dry_run):
    #     # Show error if no campaign specified?
    #     pass