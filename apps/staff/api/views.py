from typing import Any

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, status
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

from api.permissions import CuratorAccessPermission
from api.views import APIBaseView
from core.http import HttpRequest
from learning.api.serializers import StudentProfileSerializer
from learning.models import GraduateProfile
from users.filters import StudentFilter
from users.models import StudentProfile
from users.services import create_graduate_profiles


class StudentOffsetPagination(LimitOffsetPagination):
    default_limit = 500


class StudentSearchJSONView(ListAPIView):
    permission_classes = [CuratorAccessPermission]
    pagination_class = StudentOffsetPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = StudentFilter

    class OutputSerializer(StudentProfileSerializer):
        graduation_year = serializers.SerializerMethodField()

        class Meta(StudentProfileSerializer.Meta):
            fields = ('pk', 'short_name', 'user_id', 'graduation_year')

        def get_graduation_year(self, obj):
            if hasattr(obj, 'graduate_profile'):
                return obj.graduate_profile.graduation_year
            return None

    def get_serializer_class(self):
        return self.OutputSerializer

    def get_queryset(self):
        return (StudentProfile.objects
                .filter(site=self.request.site)
                .select_related('user', 'graduate_profile')
                .only('user__username', 'user__first_name',
                      'user__last_name', 'user_id')
                .order_by('user__last_name',
                          'user__first_name',
                          'user_id'))


class CreateAlumniProfiles(APIBaseView):
    permission_classes = [CuratorAccessPermission]

    class InputSerializer(serializers.Serializer):
        graduated_on = serializers.DateField()

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any):
        serializer = self.InputSerializer(data=request.POST)
        serializer.is_valid(raise_exception=True)

        graduated_on = serializer.validated_data['graduated_on']
        create_graduate_profiles(request.site, graduated_on, created_by=request.user)

        return Response(status=status.HTTP_201_CREATED)
