# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import tablib

from django.core.management import BaseCommand, CommandError

from learning.admission.import_export import OnlineTestRecordResource
from ._utils import CurrentCampaignsMixin, HandleErrorsMixin


class Command(CurrentCampaignsMixin, HandleErrorsMixin, BaseCommand):
    help = (
        """
        Deprecated. Import results for online test. Run in dry mode by default.

        Try to find already existed online test results first by `lookup` field 
        (should be unique within current campaigns)
        and update record if score is less than previous. 
        Otherwise if user tried to pass context (check by `details` 
        column content) - create new record.

        Note: Don't forget manually remove applicant duplicates first
            to avoid errors on `attach_applicant` action.
        """
    )
    # Data from columns not specified in `separated_fields` placed to
    # `details` JSON field
    separated_fields = [
        'created',
        'yandex_id',
        'stepic_id',
        'score',
        'yandex_contest_id',
        'user_name'
    ]
    lookup_fields = ["yandex_id", "stepic_id"]

    def add_arguments(self, parser):
        parser.add_argument('csv', metavar='CSV',
                            help='Path to csv with results')
        parser.add_argument(
            '--lookup',
            dest='lookup_field',
            choices=self.lookup_fields,
            default="yandex_id",
            help='Lookup attribute which store unique applicant identifier '
                 'within current campaigns')
        parser.add_argument(
            '--city', type=str,
            help='City code to restrict current campaigns')
        parser.add_argument(
            '--contest_id', type=int,
            help='Save contest_id for debug purpose. '
                 'Overrides `yandex_contest_id` field from source csv file')
        parser.add_argument(
            '--save',
            action="store_true",
            help='Skip dry mode and save imported data to DB if no errors')

    def handle(self, *args, **options):
        csv_path = options["csv"]
        lookup_field = options["lookup_field"]
        dry_run = not options["save"]
        contest_id = options["contest_id"]
        city_code = options["city"] if options["city"] else None
        campaign_ids = self.get_current_campaign_ids(city_code)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        with open(csv_path, "r") as f:
            data = tablib.Dataset().load(f.read())
            self.clean_yandex_contest_csv_headers(contest_id, data)
            online_test_resource = OnlineTestRecordResource(
                lookup_field=lookup_field,
                separated_fields=self.separated_fields,
                campaign_ids=campaign_ids,
                contest_id=contest_id)
            result = online_test_resource.import_data(data, dry_run=dry_run)
            self.handle_errors(result)
            if dry_run:
                self.stdout.write("Data not imported. Dry run mode ON.")
            else:
                self.stdout.write("Done")

    @staticmethod
    def clean_yandex_contest_csv_headers(contest_id, data):
        # We don't care about there placement in contest
        del data["place"]
        login_index = data.headers.index("login")
        data.headers[login_index] = "yandex_id"
        try:
            index = data.headers.index("Score")
            data.headers[index] = data.headers[index].lower()
        except ValueError:
            pass
        if not contest_id and "contest_id" not in data.headers:
            raise CommandError("Contest id must be provided in csv "
                               "file or pass with --contest_id arg")
