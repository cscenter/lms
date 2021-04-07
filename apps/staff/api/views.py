from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination

from api.permissions import CuratorAccessPermission
from learning.api.serializers import StudentProfileSerializer
from users.filters import StudentFilter
from users.models import StudentProfile


class StudentOffsetPagination(LimitOffsetPagination):
    default_limit = 500


class StudentSearchJSONView(ListAPIView):
    permission_classes = [CuratorAccessPermission]
    pagination_class = StudentOffsetPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = StudentFilter

    class OutputSerializer(StudentProfileSerializer):
        class Meta(StudentProfileSerializer.Meta):
            fields = ('pk', 'short_name', 'user_id')

    def get_serializer_class(self):
        return self.OutputSerializer

    def get_queryset(self):
        return (StudentProfile.objects
                .filter(site=self.request.site)
                .select_related('user')
                .only('user__username', 'user__first_name',
                      'user__last_name', 'user_id')
                .order_by('user__last_name',
                          'user__first_name',
                          'user_id'))
