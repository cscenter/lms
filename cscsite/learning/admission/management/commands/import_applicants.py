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

        parser.add_argument('--dry-run',
            action="store_true",
            help='Run in dry mode to see errors first')

    def handle(self, *args, **options):
        csv_path = options["csv"]
        dry_run = options["dry_run"]

        dataset = tablib.Dataset().load(open(csv_path).read())
        if not "campaign" in dataset.headers:
            raise CommandError("Column `campaign` with campaign_id`s not specified in source csv")
        if "id" in dataset.headers:
            raise CommandError("Sorry, you can't set `id` manually")

        applicant_resource = ApplicantRecordResource()
        result = applicant_resource.import_data(dataset, dry_run=dry_run)
        if result.has_errors():
            for error in result.base_errors:
                print(error)
            for _, error in result.row_errors():
                print(error)
        print("Done")