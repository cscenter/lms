from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination

from api.permissions import CuratorAccessPermission
from users.filters import UserFilter
from users.models import User
from .serializers import UserSearchSerializer


class StudentOffsetPagination(LimitOffsetPagination):
    default_limit = 500


class StudentSearchJSONView(ListAPIView):
    permission_classes = [CuratorAccessPermission]
    serializer_class = UserSearchSerializer
    pagination_class = StudentOffsetPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = UserFilter

    def get_queryset(self):
        return (User.objects
                .only('username', 'first_name', 'last_name', 'pk')
                .order_by('last_name', 'first_name'))
