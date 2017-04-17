# -*- coding: utf-8 -*-

from django.core.management import BaseCommand, CommandError
from django.db.models import Count

from ._utils import CurrentCampaignsMixin
from learning.admission.models import Applicant, Campaign


# FIXME: Work with yandex_id only! Remove lookup_field logic at all?
class Command(CurrentCampaignsMixin, BaseCommand):
    help = "Show applicant duplicates within current campaigns"
    lookup_fields = ["yandex_id", "stepic_id"]

    def add_arguments(self, parser):
        parser.add_argument('--lookup',
                            dest='lookup_field',
                            choices=self.lookup_fields,
                            default="yandex_id",
                            help='Lookup attribute name with unique identifier '
                                 'within current campaigns')
        parser.add_argument('--resolve',
                            action="store_true",
                            help='Auto resolve duplicates: save last added '
                                 'record, delete others')

    def handle(self, *args, **options):
        lookup_field = options["lookup_field"]
        auto_resolve = options["resolve"]
        campaign_ids = self.get_current_campaign_ids()

        if lookup_field == "yandex_id":
            lookup_field = "yandex_id_normalize"
        qs = (Applicant.objects
                       .filter(campaign_id__in=campaign_ids)
                       .values(lookup_field)
                       .annotate(num_accounts=Count(lookup_field))
                       .filter(num_accounts__gt=1))

        removed = 0
        for applicant in qs:
            # Skip empty values
            if not applicant[lookup_field]:
                continue
            if auto_resolve:
                params = {
                    "campaign_ids__in": campaign_ids,
                    lookup_field: applicant[lookup_field]
                }
                to_delete = list(Applicant.objects
                                 .filter(**params)
                                 .values_list("id", flat=True)
                                 .order_by("-id"))
                to_delete.pop(0)  # Save last one
                removed += len(to_delete)
                Applicant.objects.filter(pk__in=to_delete).delete()
            else:
                print("Applicant with {} = {}".format(lookup_field,
                                                      applicant[lookup_field]))
        print("Done")
        if auto_resolve:
            print("Summary: removed {} duplicates".format(removed))
