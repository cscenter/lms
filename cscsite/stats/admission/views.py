import json
from itertools import groupby

from django.db.models import Count, When, IntegerField, Case
from rest_framework.response import Response
from rest_framework.serializers import ListSerializer, BaseSerializer
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_pandas import PandasView
from rest_pandas.serializers import SimpleSerializer

from api.permissions import CuratorAccessPermission
from learning.admission.models import Applicant, Test, Exam
from stats.admission.pandas_serializers import ApplicantsResultsSerializer
from stats.renderers import ListRenderersMixin

TestingCountAnnotation = Count(Case(When(online_test__isnull=False, then=1),
                                    output_field=IntegerField()))
ExaminationCountAnnotation = Count(Case(When(exam__isnull=False, then=1),
                                        output_field=IntegerField()))
InterviewingCountAnnotation = Count(Case(When(interview__isnull=False, then=1),
                                         output_field=IntegerField()))


class CampaignsStagesByYears(ReadOnlyModelViewSet):
    """Admission stages by years for provided city."""
    permission_classes = [CuratorAccessPermission]

    def list(self, request, *args, **kwargs):
        city_code = self.kwargs.get('city_code')
        applicants = (Applicant.objects
                      .filter(campaign__city_id=city_code)
                      .values('campaign_id', 'campaign__year')
                      .annotate(application_form=Count("campaign_id"),
                                testing=TestingCountAnnotation,
                                examination=ExaminationCountAnnotation,
                                interviewing=InterviewingCountAnnotation)
                      # Under the assumption that campaign year is unique
                      .order_by('campaign__year'))
        return Response(applicants)


class CampaignStagesByUniversities(ReadOnlyModelViewSet):
    """Admission campaign stages by universities."""
    permission_classes = [CuratorAccessPermission]

    def list(self, request, *args, **kwargs):
        campaign_id = self.kwargs.get('campaign_id')
        applicants = (Applicant.objects
                      .filter(campaign_id=campaign_id)
                      .values('university_id', 'university__name')
                      .annotate(application_form=Count("campaign_id"),
                                testing=TestingCountAnnotation,
                                examination=ExaminationCountAnnotation,
                                interviewing=InterviewingCountAnnotation)
                      )
        return Response(applicants)


class CampaignStagesByCourses(ReadOnlyModelViewSet):
    """Admission campaign stages by courses."""
    permission_classes = [CuratorAccessPermission]

    def list(self, request, *args, **kwargs):
        campaign_id = self.kwargs.get('campaign_id')
        applicants = (Applicant.objects
                      .filter(campaign_id=campaign_id)
                      .values('course')
                      .annotate(application_form=Count("campaign_id"),
                                testing=TestingCountAnnotation,
                                examination=ExaminationCountAnnotation,
                                interviewing=InterviewingCountAnnotation)
                      )
        # TODO: Add serializers for course name
        return Response(applicants)


class CampaignStatsApplicantsResults(ListRenderersMixin, PandasView):
    """Admission campaign results by applicants"""
    permission_classes = [CuratorAccessPermission]
    serializer_class = SimpleSerializer
    pandas_serializer_class = ApplicantsResultsSerializer

    def get_queryset(self):
        STATUSES = [Applicant.ACCEPT,
                    Applicant.ACCEPT_IF,
                    Applicant.REJECTED_BY_INTERVIEW,
                    Applicant.VOLUNTEER,
                    Applicant.THEY_REFUSED]
        city_code = self.kwargs.get('city_code')
        qs = (Applicant.objects
              .filter(campaign__city_id=city_code,
                      status__in=STATUSES)
              .values('campaign__year', 'status')
              .annotate(total=Count("status"))
              # Under the assumption that campaign year is unique.
              .order_by('campaign__year'))
        return qs


class CampaignStatsStudentsResults(ReadOnlyModelViewSet):
    """
    Students academic progress who enrolled in provided admission campaign.
    """
    permission_classes = [CuratorAccessPermission]

    def list(self, request, *args, **kwargs):
        return Response({})


class CampaignStatsOnlineTestScore(ReadOnlyModelViewSet):
    """Distribution of online test results by scores."""
    permission_classes = [CuratorAccessPermission]

    def list(self, request, *args, **kwargs):
        campaign_id = self.kwargs.get('campaign_id')
        qs = (Test.objects
              .filter(applicant__campaign_id=campaign_id)
              .values('score')
              .annotate(total=Count('score')))
        return Response(qs)


class CampaignStatsExamScore(ReadOnlyModelViewSet):
    """Distribution of exam results by scores."""
    permission_classes = [CuratorAccessPermission]

    def list(self, request, *args, **kwargs):
        campaign_id = self.kwargs.get('campaign_id')
        qs = (Exam.objects
              .filter(applicant__campaign_id=campaign_id)
              .values('score')
              .annotate(total=Count('score')))
        return Response(qs)
