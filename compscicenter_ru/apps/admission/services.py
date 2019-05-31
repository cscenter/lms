import datetime
from operator import attrgetter
from typing import List

from django.db import transaction
from django.utils import timezone

from admission.constants import INVITATION_EXPIRED_IN_HOURS
from admission.models import InterviewStream, InterviewInvitation, \
    Applicant


def create_invitation(streams: List[InterviewStream], applicant: Applicant):
    """Create invitation and send email to applicant."""
    streams = list(streams)  # Queryset -> list
    first_stream = min(streams, key=attrgetter('date'))
    first_day_interview = datetime.datetime(
        first_stream.date.year,
        first_stream.date.month,
        first_stream.date.day,
        tzinfo=first_stream.get_city_timezone())
    # Calculate deadline for invitation. It can't be later than 00:00
    # of the first interview day
    expired_in_hours = INVITATION_EXPIRED_IN_HOURS
    expired_at = timezone.now() + datetime.timedelta(hours=expired_in_hours)
    expired_at = min(expired_at, first_day_interview)
    invitation = InterviewInvitation(applicant=applicant,
                                     expired_at=expired_at)
    with transaction.atomic():
        invitation.save()
        invitation.streams.add(*streams)
        invitation.send_email()
