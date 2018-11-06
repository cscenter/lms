# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import tablib
from django.core.management import BaseCommand, CommandError

from admission.import_export import ExamRecordResource
from ._utils import CurrentCampaignsMixin, HandleErrorsMixin


# TODO: Сделать город обязательным. Для записей, которые не подходят по городу
# - прятать сообщения о том, что не найдена анкета. Для этого надо переделать
# логику поиска анкет - сначала искать по yandex_id, потом уже отфильтровывать
# по городу
class Command(HandleErrorsMixin, CurrentCampaignsMixin, BaseCommand):
    help = (
        """Import results for online exam. Run in dry mode by default.

        Try to find already existed exam record by `lookup` field
        and campaign_id and update record. Otherwise fail.
        Note: This command doesn't create records.
            Run `exam_import_step1` first to create empty records.
        """
    )
    # Other fields go to dynamically created `details` field
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
        parser.add_argument(
            '--contest_id', type=int,
            help='Set contest_id. Overrides `yandex_contest_id`'
                 ' field from source csv file')

    def handle(self, *args, **options):
        csv_path = options["csv"]
        lookup_field = options["lookup_field"]
        city_code = options["city"] if options["city"] else None
        campaign_ids = self.get_current_campaign_ids(city_code)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return
        dry_run = not options["save"]
        contest_id = options["contest_id"]

        with open(csv_path, "r") as f:
            data = tablib.Dataset().load(f.read())
            self.clean_yandex_contest_csv_headers(contest_id, data)
            online_exam_resource = ExamRecordResource(
                lookup_field=lookup_field,
                separated_fields=self.separated_fields,
                campaign_ids=campaign_ids,
                contest_id=contest_id)
            result = online_exam_resource.import_data(data, dry_run=dry_run)
            self.handle_errors(result)
            if dry_run:
                self.stdout.write("Data not imported. Dry run mode ON.")
            else:
                print("Done")

    @staticmethod
    def clean_yandex_contest_csv_headers(contest_id, data):
        # Clean some headers before run import
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
