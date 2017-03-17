# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import tablib
from django.core.management import BaseCommand, CommandError

from learning.admission.import_export import ExamRecordResource


class Command(BaseCommand):
    help = (
        """Import results for online exam. Run in dry mode by default.

        Try to find already existed exam record by `lookup` field
        and campaign_id and update record. Otherwise fail.
        Note: This command doesn't create records.
            Run `exam_import_step1` first to create empty records.

        Example:
        ./manage.py exam_import_step2 ~/2444.csv --campaign_ids=1,2,3
        """
    )
    # Other fields go to dynamically created `details` field
    allowed_fields = ['created', 'yandex_id', 'stepic_id', 'score',
                      'yandex_contest_id', 'user_name']
    lookup_fields = ["yandex_id", "stepic_id"]

    def add_arguments(self, parser):
        parser.add_argument('csv', metavar='CSV',
                            help='path to csv with data')

        parser.add_argument('--campaign_ids', type=str,
                            dest='campaign_ids',
                            help='Comma separated campaign ids')

        parser.add_argument(
            '--lookup',
            dest='lookup_field',
            choices=self.lookup_fields,
            default="yandex_id",
            help='Lookup attribute which store unique applicant identifier '
                 'in provided campaigns')

        parser.add_argument(
            '--save',
            action="store_true",
            help='Skip dry mode and import data to DB')

        parser.add_argument(
            '--passing_score', type=int,
            help='You can pass value to set `rejected by online exam` '
                 'status for applicants below passing score')

        parser.add_argument(
            '--contest_id', type=int,
            help='Saves contest_id. Overrides `yandex_contest_id`'
                 ' field from source csv file')

    def handle(self, *args, **options):
        csv_path = options["csv"]
        lookup_field = options["lookup_field"]
        campaign_ids = self.clean_campaigns(options)
        passing_score = options["passing_score"]
        dry_run = not options["skip"]
        contest_id = options["contest_id"]

        with open(csv_path, "rb") as f:
            data = tablib.Dataset().load(f.read())
            if not contest_id and "contest_id" not in data.headers:
                raise CommandError("Contest id must be provided in csv "
                                   "file or pass with --contest_id arg")
            online_exam_resource = ExamRecordResource(
                lookup_field=lookup_field,
                allowed_fields=self.allowed_fields,
                campaign_id=campaign_ids,
                passing_score=passing_score,
                contest_id=contest_id)
            result = online_exam_resource.import_data(data, dry_run=dry_run)
            self.handle_errors(result)
            if dry_run:
                print("Dry run completed")
            else:
                print("Done")

    @staticmethod
    def clean_campaigns(options):
        if not options["campaign_ids"]:
            raise CommandError("Campaign ID's not specified")
        campaign_ids = options["campaign_ids"].split(",")
        try:
            campaign_ids = [int(cid) for cid in campaign_ids]
        except (TypeError, ValueError):
            raise CommandError("Campaign ID's are not comma separated integers")
        return campaign_ids

    @staticmethod
    def handle_errors(result):
        if result.has_errors():
            for error in result.base_errors:
                print(error)
            for line, errors in result.row_errors():
                for error in errors:
                    print("line {} - {}".format(line + 1, error.error))
