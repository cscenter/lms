import csv

from django.db import transaction

from admission.models import Applicant


def main():
    with open('notes.csv') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        next(reader, None)  # skip the headers
        prefix = '/admission/applicants/'
        with transaction.atomic():
            for row in reader:
                note, applicant_url = row[-2:]
                assert applicant_url.startswith(prefix)
                assert applicant_url[-1] == '/'
                applicant_id = int(applicant_url[len(prefix):-1])
                assert Applicant.objects.filter(pk=applicant_id).update(admin_note=note)
                print(applicant_id, note)


main()
