from datetime import datetime, timedelta
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
    tz = first_stream.get_city_timezone()
    first_day_interview_naive = datetime.combine(first_stream.date,
                                                 datetime.min.time())
    first_day_interview = tz.localize(first_day_interview_naive)
    # Calculate deadline for invitation. It can't be later than 00:00
    # of the first interview day
    expired_in_hours = INVITATION_EXPIRED_IN_HOURS
    expired_at = timezone.now() + timedelta(hours=expired_in_hours)
    expired_at = min(expired_at, first_day_interview)
    invitation = InterviewInvitation(applicant=applicant,
                                     expired_at=expired_at)
    with transaction.atomic():
        invitation.save()
        invitation.streams.add(*streams)
        invitation.send_email()
