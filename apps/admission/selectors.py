from typing import List, Optional
from uuid import uuid4

from django.db.models import Q

from admission.constants import InterviewInvitationStatuses
from admission.models import InterviewInvitation, InterviewSlot
from core.timezone import get_now_utc


def get_occupied_slot(*, invitation: InterviewInvitation) -> Optional[InterviewSlot]:
    slot = (InterviewSlot.objects
            .filter(interview_id=invitation.interview_id,
                    interview__applicant_id=invitation.applicant_id)
            .select_related("stream__interview_format",
                            "interview__applicant__campaign")
            .first())
    # Interview could be reassigned to another applicant
    # after the slot was occupied
    if slot.interview.applicant_id != invitation.applicant_id:
        return None
    return slot


def get_interview_invitation(*, year: int, secret_code: uuid4,
                             filters: List[Q] = None) -> Optional[InterviewInvitation]:
    filters = filters or []
    try:
        return (InterviewInvitation.objects
                .filter(*filters,
                        secret_code=secret_code,
                        applicant__campaign__year=year)
                .select_related("applicant__campaign")
                .get())
    except InterviewInvitation.DoesNotExist:
        return None


def get_ongoing_interview_invitation(*, year: int, secret_code: uuid4) -> Optional[InterviewInvitation]:
    """
    *Ongoing* means that interview invitation is not expired or declined and
    the participant could accept or decline it before the deadline if they
    haven't already done so.
    """
    filters = [
        Q(expired_at__gt=get_now_utc()),
        ~Q(status=InterviewInvitationStatuses.DECLINED)
    ]
    return get_interview_invitation(year=year, secret_code=secret_code,
                                    filters=filters)
