# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from itertools import chain

import tablib

from django.core.management import BaseCommand, CommandError

from learning.admission.import_export import OnlineTestRecordResource
from learning.admission.models import Applicant


class Command(BaseCommand):
    help = (
        "Import results for online test."

        "Try to find already existed online test by (`lookup` field "
        "and campaign_id OR `uuid` value) and update record if score is less than previous."
        "Note: Don't forget manually remove applicant duplicates first "
        "to avoid errors on `attach_applicant` action."
        "Note: Dynamically add `details` and `applicant` columns if not specified."
        "Note: add `uuid` field to avoid duplicates"
    )
    # Other fields go to dynamically created `details` field
    allowed_fields = ['created', 'yandex_id', 'stepic_id', 'score']
    lookup_fields = ["yandex_id", "stepic_id"]

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument('csv', metavar='CSV',
                   help='path to csv with data')

        parser.add_argument('--campaign_id', type=int,
            dest='campaign_id',
            help='Search applicant profile by specified campaign id')

        parser.add_argument('--lookup',
            dest='lookup_field',
            choices=self.lookup_fields,
            default="yandex_id",
            help='Lookup for applicant instance by specified field and `campaign`')

        parser.add_argument('--dry-run',
            action="store_true",
            help='Run in dry mode to see errors first')

        parser.add_argument('--passing_score', type=int,
            help='Set `rejected by online test` status for applicants below passing score')

    def handle(self, *args, **options):
        csv_path = options["csv"]
        campaign_id = options["campaign_id"]
        dry_run = options["dry_run"]
        if not campaign_id:
            raise CommandError("Campaign ID not specified")
        lookup_field = options["lookup_field"]
        passing_score = options["passing_score"]
        if not passing_score:
            raise CommandError("Passing score not specified")

        # TODO: Не забыть выставлять статус (не прошёл по результатам теста);
        # TODO: не более 1го теста экзамена на заявку. Проверять эту шнягу

        def collect_details(headers):
            """Collect data for `details` column"""
            def wrapper(row):
                details = {}
                for i, h in enumerate(headers):
                    if h not in self.allowed_fields:
                        details[h] = row[i]
                return details
            return wrapper

        def attach_applicant(headers, lookup_field, campaign_id):
            """Find applicant by lookup field and campaign id. Return empty
            string if can't find applicant"""
            def wrapper(row):
                qs = Applicant.objects.filter(campaign_id=campaign_id)
                index  = headers.index(lookup_field)
                if not row[index]:
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

        with open(csv_path, "rb") as f:
            data = tablib.Dataset().load(f.read())
            if not lookup_field in data.headers:
                raise CommandError("lookup field not specified in source csv")
            if "details" in data.headers:
                print("Column `details` will be ignored")
                del data["details"]
            data.append_col(collect_details(data.headers), header="details")
            if "applicant" not in data.headers:
                data.append_col(
                    attach_applicant(data.headers, lookup_field, campaign_id),
                    header="applicant")

            # TODO: Сначала надо удалить записи с пустым applicant. Затем, если был найден instance -  обновить у него score, обновить статус applicant, если score ниже passing_score

            online_test_resource = OnlineTestRecordResource()
            result = online_test_resource.import_data(data, dry_run=dry_run)
            if result.has_errors():
                for error in result.base_errors:
                    print(error)
                for _, error in result.row_errors():
                    print(error)
            else:
                print("Finish")
