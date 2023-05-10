import csv

from django.db import transaction

from admission.constants import ApplicantStatuses
from admission.models import Applicant, Campaign


def main():
    threshold = 20
    campaigns_pk = [35, 36, 39]
    campaigns = Campaign.objects.filter(pk__in=campaigns_pk)
    with transaction.atomic():
        success = Applicant.objects.filter(
            campaign__in=campaigns,
            exam__score__gte=threshold
        )
        failed = (Applicant.objects
                  .filter(campaign__in=campaigns)
                  .exclude(exam__score__gte=threshold)
                  )
        assert success.count() + failed.count() == Applicant.objects.filter(campaign__in=campaigns_pk).count()
        print(f"Success: {success.count()}\n"
              f"Failed: {failed.count()}\n"
              f"Total: {Applicant.objects.filter(campaign__in=campaigns_pk).count()}\n")
        assert success.update(status=ApplicantStatuses.INTERVIEW_TOBE_SCHEDULED)
        assert failed.update(status=ApplicantStatuses.REJECTED_BY_EXAM)


main()
