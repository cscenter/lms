# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import uuid

import tablib
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = """Attach new column with `uuid`"""

    def add_arguments(self, parser):
        parser.add_argument('csv', metavar='CSV', help='path to original csv')

    def handle(self, *args, **options):
        csv_path = options["csv"]
        filename, file_extension = os.path.splitext(csv_path)
        count = 0
        new_csv_path = "{}_new{}{}".format(filename, count, file_extension)
        while os.path.exists(new_csv_path):
            count += 1
            new_csv_path = "{}_new{}{}".format(filename, count, file_extension)

        dataset = tablib.Dataset().load(open(csv_path).read())
        dataset.append_col(lambda r: uuid.uuid4(), header='uuid')

        with open(new_csv_path, 'w') as f:
            f.write(dataset.csv)
        self.stdout.write("File {} was generated".format(new_csv_path))
