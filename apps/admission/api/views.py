from typing import Any, List, Type

from rest_framework import serializers, status
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import ParseError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings
from django.db.models import Q
from django.http import Http404

from admission.models import InterviewSlot, ResidenceCity
from admission.selectors import (
    get_ongoing_interview_invitation,
    residence_cities_queryset,
    residence_city_campaigns_queryset,
)
from admission.services import (
    accept_interview_invitation,
    create_contest_results_import_task,
    decline_interview_invitation,
    get_acceptance_ready_to_confirm,
    send_email_verification_code,
)
from admission.tasks import import_campaign_contest_results
from api.permissions import CuratorAccessPermission
from api.utils import inline_serializer
from api.views import APIBaseView
from core.api.serializers import BranchSerializer
from core.http import APIRequest, HttpRequest
from core.models import Branch

from ..constants import ContestTypes
from .serializers import InterviewSlotBaseSerializer


class InterviewSlots(APIView):
    """
    Returns all slots for requested interview streams
    """

    permission_classes = [CuratorAccessPermission]

    def get(self, request, *args, **kwargs):
        slots = InterviewSlot.objects.none()
        if "streams[]" in request.GET:
            try:
                streams = [int(v) for v in request.GET.getlist("streams[]")]
            except ValueError:
                raise ParseError()
            slots = (
                InterviewSlot.objects.filter(stream_id__in=streams)
                .select_related("stream")
                .order_by("stream__date", "start_at")
            )
        serializer = InterviewSlotBaseSerializer(slots, many=True)
        return Response(serializer.data)


class AppointmentInterviewInvitationApi(APIBaseView):
    """View to decline interview invitation"""

    permission_classes = (AllowAny,)

    class InputSerializer(serializers.Serializer):
        year = serializers.IntegerField()
        secret_code = serializers.UUIDField()

    def put(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=kwargs)
        serializer.is_valid(raise_exception=True)

        invitation = get_ongoing_interview_invitation(**serializer.validated_data)
        if not invitation:
            raise Http404

        decline_interview_invitation(invitation)

        return Response(status=status.HTTP_200_OK)


class AppointmentInterviewCreateApi(APIBaseView):
    """View to accept interview invitation"""

    permission_classes = (AllowAny,)

    class InputSerializer(serializers.Serializer):
        year = serializers.IntegerField()
        secret_code = serializers.UUIDField(format="hex_verbose")
        slot_id = serializers.IntegerField()

    def post(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=kwargs)
        serializer.is_valid(raise_exception=True)
        invitation = get_ongoing_interview_invitation(
            year=serializer.validated_data["year"],
            secret_code=serializer.validated_data["secret_code"],
        )
        if not invitation:
            raise Http404

        accept_interview_invitation(
            invitation, slot_id=serializer.validated_data["slot_id"]
        )

        return Response(status=status.HTTP_201_CREATED)


class ConfirmationSendEmailVerificationCodeApi(APIBaseView):
    """Sends verification code to email"""

    permission_classes = (AllowAny,)

    class InputSerializer(serializers.Serializer):
        year = serializers.IntegerField()
        access_key = serializers.CharField()
        email = serializers.EmailField()

    def post(self, request: HttpRequest, *args, **kwargs):
        serializer = self.InputSerializer(data=request.POST)
        serializer.is_valid(raise_exception=True)

        branches = Branch.objects.for_site(site_id=settings.SITE_ID)
        acceptance = get_acceptance_ready_to_confirm(
            year=serializer.validated_data["year"],
            access_key=serializer.validated_data["access_key"],
            filters=[Q(applicant__campaign__branch__in=branches)],
        )
        if not acceptance:
            raise Http404

        send_email_verification_code(
            email_to=serializer.validated_data["email"],
            site=request.site,
            applicant=acceptance.applicant,
        )

        return Response(status=status.HTTP_201_CREATED, data={})


class CampaignCreateContestScoresImportTask(APIBaseView):
    """Creates a new task for importing scores from yandex contests."""

    permission_classes = [CuratorAccessPermission]

    class InputSerializer(serializers.Serializer):
        campaign_id = serializers.IntegerField()
        contest_type = serializers.ChoiceField(choices=ContestTypes.choices)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any):
        serializer = self.InputSerializer(data=kwargs)
        serializer.is_valid(raise_exception=True)

        task = create_contest_results_import_task(
            campaign=serializer.validated_data["campaign_id"],
            contest_type=serializer.validated_data["contest_type"],
            author=request.user,
        )
        # FIXME: Potentially we could duplicate task in a redis (e.g. with a subsequent calls to this API). How to avoid this? compare created/modified times?
        import_campaign_contest_results.delay(task_id=task.pk)
        return Response(status=status.HTTP_201_CREATED, data={"id": task.pk})


class ResidenceCityList(APIBaseView):
    authentication_classes: List[Type[BaseAuthentication]] = []
    permission_classes = (AllowAny,)

    class FilterSerializer(serializers.Serializer):
        country_id = serializers.IntegerField(required=False)
        ordering = serializers.CharField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        name = serializers.CharField(source="display_name")

        class Meta:
            model = ResidenceCity
            fields = ("id", "country_id", "name")

    def get(self, request: APIRequest, **kwargs: Any):
        filters_serializer = self.FilterSerializer(data=request.query_params)
        filters_serializer.is_valid(raise_exception=True)
        residence_cities = residence_cities_queryset(
            filters=filters_serializer.validated_data
        )
        data = self.OutputSerializer(residence_cities, many=True).data
        return Response(data)


class CampaignCityList(APIBaseView):
    authentication_classes: List[Type[BaseAuthentication]] = []
    permission_classes = (AllowAny,)

    class FilterSerializer(serializers.Serializer):
        city_id = serializers.IntegerField(required=True)
        ordering = serializers.CharField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        campaign = inline_serializer(
            fields={
                "id": serializers.IntegerField(),
                "branch": inline_serializer(
                    fields={
                        "code": serializers.CharField(),
                        "name": serializers.CharField(),
                    }
                ),
            }
        )

        class Meta:
            model = ResidenceCity
            fields = ("id", "campaign")

    def get(self, request: APIRequest, **kwargs: Any):
        filters_serializer = self.FilterSerializer(data=request.query_params)
        filters_serializer.is_valid(raise_exception=True)
        residence_city_campaigns = residence_city_campaigns_queryset(
            filters=filters_serializer.validated_data
        )
        data = self.OutputSerializer(residence_city_campaigns, many=True).data
        return Response(data)
