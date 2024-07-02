from typing import Any, Dict, List, Optional
from uuid import UUID

from django.utils import timezone
from django_filters import NumberFilter, OrderingFilter
from django_filters.rest_framework import FilterSet
from rest_framework.exceptions import ValidationError

from django.db.models import Q, QuerySet

from admission.constants import InterviewInvitationStatuses
from admission.models import (
    Acceptance,
    InterviewInvitation,
    InterviewSlot,
    ResidenceCity,
    CampaignCity
)
from core.timezone import get_now_utc

UUID4 = UUID


def get_occupied_slot(*, invitation: InterviewInvitation) -> Optional[InterviewSlot]:
    slot = (
        InterviewSlot.objects.filter(
            interview_id=invitation.interview_id,
            interview__applicant_id=invitation.applicant_id,
        )
        .select_related("stream__interview_format", "interview__applicant__campaign")
        .first()
    )
    if slot is None:
        return None
    # Interview could be reassigned to another applicant
    # after the slot was occupied
    if slot.interview.applicant_id != invitation.applicant_id:
        return None
    return slot


def get_interview_invitation(
    *, year: int, secret_code: UUID4, filters: Optional[List[Q]] = None
) -> Optional[InterviewInvitation]:
    filters = filters or []
    try:
        return (
            InterviewInvitation.objects.filter(
                *filters, secret_code=secret_code, applicant__campaign__year=year
            )
            .select_related("applicant__campaign")
            .get()
        )
    except InterviewInvitation.DoesNotExist:
        return None


def get_ongoing_interview_invitation(
    *, year: int, secret_code: UUID4
) -> Optional[InterviewInvitation]:
    """
    *Ongoing* means that interview invitation is not expired or declined and
    the participant could accept or decline it before the deadline if they
    haven't already done so.
    """
    filters = [
        Q(expired_at__gt=get_now_utc()),
        ~Q(status=InterviewInvitationStatuses.DECLINED),
    ]
    return get_interview_invitation(year=year, secret_code=secret_code, filters=filters)


def get_acceptance(
    *, year: int, access_key: str, filters: Optional[List[Q]] = None
) -> Optional[Acceptance]:
    filters = filters or []
    try:
        return (
            Acceptance.objects.filter(
                *filters, access_key=access_key, applicant__campaign__year=year
            )
            .select_related(
                "applicant__campaign__branch",
                "applicant__university",
                "applicant__university_legacy",
            )
            .get()
        )
    except Acceptance.DoesNotExist:
        return None


class ResidenceCityFilter(FilterSet):
    country_id = NumberFilter(lookup_expr="exact", required=False)

    ordering = OrderingFilter(
        fields=[("order", "order"), ("display_name", "name")],
        field_labels={
            "order": "Order",
            "display_name": "Display Name",
        },
    )

    class Meta:
        model = ResidenceCity
        fields = ("country_id", "ordering")


def residence_cities_queryset(
    *, filters: Optional[Dict[str, Any]] = None
) -> QuerySet[ResidenceCity]:
    filter_set = ResidenceCityFilter(filters, ResidenceCity.objects.get_queryset())
    if filter_set.is_bound and not filter_set.is_valid():
        raise ValidationError(filter_set.errors)
    if "ordering" in filters:
        return filter_set.qs
    return filter_set.qs.order_by()


class CampaignCityFilter(FilterSet):
    city_id = NumberFilter(lookup_expr="exact", required=False)

    ordering = OrderingFilter(
        fields=[("campaign__order", "campaign")],
        field_labels={
            "campaign": "Campaign Order",
        },
    )

    class Meta:
        model = ResidenceCity
        fields = ("city_id", "ordering")


def residence_city_campaigns_queryset(
    *, filters: Optional[Dict[str, Any]] = None
) -> QuerySet[CampaignCity]:
    filter_set = CampaignCityFilter(filters, CampaignCity.objects.get_queryset())
    if filter_set.is_bound and not filter_set.is_valid():
        raise ValidationError(filter_set.errors)
    if "ordering" in filters:
        return filter_set.qs
    return filter_set.qs.order_by()

def get_ongoing_interviews(user):
    return (interview for interview in user.interview_set.select_related('slot__stream')
            if interview.slot.datetime_local >= timezone.now())
