import csv

from django.db import transaction

from admission.models import Applicant


def main():
    with open('notes.csv') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        prefix = '/admission/applicants/'
        commit = True
        with transaction.atomic():
            for row in reader:
                note, applicant_url = row['Заметки'], row['ID']
                assert applicant_url.startswith(prefix)
                assert applicant_url[-1] == '/'
                applicant_id = int(applicant_url[len(prefix):-1])
                assert Applicant.objects.filter(pk=applicant_id).update(admin_note=note)
                print(applicant_id, note)
            if not commit:
                raise Exception("Please set value commit = True")

main()
