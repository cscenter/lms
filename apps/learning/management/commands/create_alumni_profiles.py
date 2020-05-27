# -*- coding: utf-8 -*-
from datetime import datetime

from django.contrib.sites.models import Site
from django.core.management import BaseCommand

from users.services import create_graduate_profiles


class Command(BaseCommand):
    help = "Create graduate profiles for students who will graduate soon"

    def add_arguments(self, parser):
        parser.add_argument('site_id', type=int, metavar='SITE_ID')
        parser.add_argument('graduated_on', metavar='GRADUATION_DATE',
                            help='Graduation date in dd.mm.yyyy format')

    def handle(self, *args, **options):
        site_id = options['site_id']
        site = Site.objects.get(pk=site_id)
        graduated_on_str = options['graduated_on']
        graduated_on = datetime.strptime(graduated_on_str, "%d.%m.%Y").date()
        create_graduate_profiles(site, graduated_on)
