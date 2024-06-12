import csv

from django.db import transaction

from admission.constants import ChallengeStatuses, ApplicantStatuses
from admission.models import Exam, Applicant


def main():
    with open('results.csv') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        next(reader, None)  # skip the headers
        contest_id = None
        exam_pass_threshold = 3
        prefix = '/admission/applicants/'
        exam_failed_pk, exam_passed_pk = [], []
        with transaction.atomic():
            for row in reader:
                score, applicant_url = row[-2:]
                assert applicant_url.startswith(prefix)
                assert applicant_url[-1] == '/'
                applicant_id = int(applicant_url[len(prefix):-1])
                print(applicant_url[len(prefix):-1])
                score = float(score.replace(',', '.'))
                if score >= exam_pass_threshold:
                    exam_passed_pk.append(applicant_id)
                else:
                    exam_failed_pk.append(applicant_id)
                obj, created = Exam.objects.get_or_create(
                    applicant_id=applicant_id,
                    score=score,
                    yandex_contest_id=contest_id,
                    status=ChallengeStatuses.MANUAL,
                    details={}
                )
                assert created
            (Applicant.objects
             .filter(pk__in=exam_passed_pk)
             .update(status=ApplicantStatuses.PASSED_EXAM))
            (Applicant.objects
             .filter(pk__in=exam_failed_pk)
             .update(status=ApplicantStatuses.REJECTED_BY_EXAM))

main()
