
import csv
import io
from django.core.management import BaseCommand

class Command(BaseCommand):
    help = "Dump enrollments csv and upload to yandex disk"

    def handle(self, *args, **options):
        with io.StringIO() as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(['ID', 'Header2', 'Header3'])


