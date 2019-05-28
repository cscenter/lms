# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import tablib
from django.core.management import BaseCommand, CommandError

from admission.import_export import ExamRecordResource
from ._utils import CurrentCampaignsMixin, HandleErrorsMixin


# TODO: Сделать город обязательным.
class Command(HandleErrorsMixin, CurrentCampaignsMixin, BaseCommand):
    help = """
    Import results for online exam. Run in dry mode by default.
    """
    lookup_fields = ["yandex_id", "stepic_id"]

    def add_arguments(self, parser):
        parser.add_argument('csv', metavar='CSV',
                            help='path to csv with data')
        parser.add_argument(
            '--lookup',
            dest='lookup_field',
            choices=self.lookup_fields,
            default="yandex_id",
            help='Lookup attribute which store unique applicant identifier '
                 'within selected current campaigns')
        parser.add_argument(
            '--city', type=str,
            help='City code to restrict current campaigns')
        parser.add_argument(
            '--save',
            action="store_true",
            help='Skip dry mode and import data to DB')

    def handle(self, *args, **options):
        csv_path = options["csv"]
        lookup_field = options["lookup_field"]
        city_code = options["city"] if options["city"] else None
        campaign_ids = self.get_current_campaign_ids(city_code)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return
        dry_run = not options["save"]

        with open(csv_path, "r") as f:
            data = tablib.Dataset().load(f.read())
            online_exam_resource = ExamRecordResource(
                lookup_field=lookup_field,
                campaign_ids=campaign_ids)
            result = online_exam_resource.import_data(data, dry_run=dry_run)
            self.handle_errors(result)
            if dry_run:
                self.stdout.write("Data not imported. Dry run mode ON.")
            else:
                print("Done")
