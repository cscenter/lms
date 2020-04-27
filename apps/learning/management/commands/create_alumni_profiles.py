# -*- coding: utf-8 -*-
from datetime import datetime

from django.core.management import BaseCommand

from learning.services import create_graduate_profiles


class Command(BaseCommand):
    help = "Create alumni profiles for students who will graduate soon"

    def add_arguments(self, parser):
        parser.add_argument('graduated_on', metavar='GRADUATION_DATE',
                            help='Graduation date in dd.mm.yyyy format')

    def handle(self, *args, **options):
        graduated_on_str = options['graduated_on']
        graduated_on = datetime.strptime(graduated_on_str, "%d.%m.%Y").date()
        create_graduate_profiles(graduated_on)
