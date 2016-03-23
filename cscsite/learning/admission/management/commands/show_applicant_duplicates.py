# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import tablib
from itertools import chain

from django.core.management import BaseCommand, CommandError
from django.db.models import Count

from learning.admission.import_export import ApplicantRecordResource
from learning.admission.models import Applicant


class Command(BaseCommand):
    help = (
        "Show applicant duplicates for specified campaign id"
    )

    lookup_fields = ["yandex_id", "stepic_id"]

    def add_arguments(self, parser):
        parser.add_argument('--campaign_id', type=int,
            dest='campaign_id',
            help='Search applicant profile by specified campaign id')

        parser.add_argument('--lookup',
            dest='lookup_field',
            choices=self.lookup_fields,
            default="yandex_id",
            help='Lookup for applicant instance by specified field and `campaign`')

        parser.add_argument('--resolve',
            action="store_true",
            help='Auto resolve duplicates: save last added record, delete others')

    def handle(self, *args, **options):
        campaign_id = options["campaign_id"]
        if not campaign_id:
            raise CommandError("Campaign ID not specified")
        lookup_field = options["lookup_field"]
        auto_resolve = options["resolve"]

        qs = (Applicant.objects
                       .filter(campaign_id=campaign_id)
                       .values(lookup_field)
                       .annotate(num_accounts=Count(lookup_field))
                       .filter(num_accounts__gt=1)
              )

        duplicates_cnt = 0
        for applicant in qs:
            # Skip empty values
            if not applicant[lookup_field]:
                continue
            if auto_resolve:
                params = {
                    "campaign_id": campaign_id,
                    lookup_field: applicant[lookup_field]
                }
                ids = list(Applicant.objects.filter(**params).values_list("id", flat=True).order_by("-id"))
                ids.pop(0)  # save
                duplicates_cnt += len(ids)
                Applicant.objects.filter(pk__in=ids).delete()
            else:
                print("Check applicant with {}={}".format(lookup_field, applicant[lookup_field]))

        print("Done")
        if auto_resolve:
            print("Successfully removed {} duplicates".format(duplicates_cnt))


