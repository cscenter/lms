# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import tablib
from itertools import chain

from django.core.management import BaseCommand, CommandError

from learning.admission.import_export import ApplicantRecordResource


class Command(BaseCommand):
    help = (
        "Import applicants from csv"

        "Note: add `uuid` field to avoid duplicates"
    )

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument('csv', metavar='CSV',
                   help='path to csv with data')
        parser.add_argument('--campaign_id', type=int,
                            dest='campaign_id',
                            help='Applicant will be associated with provided campaign id. Overrides value from csv')
        parser.add_argument('--dry-run',
            action="store_true",
            help='Run in dry mode to see errors first')

    def handle(self, *args, **options):
        csv_path = options["csv"]
        campaign_id = options["campaign_id"]
        dry_run = options["dry_run"]

        dataset = tablib.Dataset().load(open(csv_path).read())
        column_campaign_in_headers = "campaign" in dataset.headers
        if not column_campaign_in_headers and not campaign_id:
            raise CommandError("Arg `--campaign_id` or column `campaign` in csv not specified")
        if campaign_id:
            if column_campaign_in_headers:
                del dataset["campaign"]
            dataset.append_col(lambda r: campaign_id, header="campaign")
        if "id" in dataset.headers:
            raise CommandError("Sorry, you can't set `id` manually")
        applicant_resource = ApplicantRecordResource()
        result = applicant_resource.import_data(dataset, dry_run=dry_run)
        self.handle_errors(result)
        print("Done")

    def handle_errors(self, result):
        if result.has_errors():
            for error in result.base_errors:
                print(error)
            for line, errors in result.row_errors():
                for error in errors:
                    print("line {} - {}".format(line + 1, error.error))