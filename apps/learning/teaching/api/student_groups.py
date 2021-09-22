from typing import Any

from rest_framework import serializers, status
from rest_framework.response import Response

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404

from api.views import APIBaseView
from auth.mixins import RolePermissionRequiredMixin
from core.http import HttpRequest
from learning.models import Enrollment, StudentGroup
from learning.permissions import UpdateStudentGroup
from learning.services import StudentGroupService
from learning.teaching.utils import get_student_groups_url


class StudentGroupTransferStudentsView(RolePermissionRequiredMixin, APIBaseView):
    student_group: StudentGroup
    permission_classes = [UpdateStudentGroup]

    class InputSerializer(serializers.Serializer):
        student_group = serializers.PrimaryKeyRelatedField(
            required=True,
            queryset=StudentGroup.objects.get_queryset())
        ids = serializers.ListField(
            label="Student Profiles",
            child=serializers.IntegerField(min_value=1),
            min_length=1,
            allow_empty=False)

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any):
        super().setup(request, *args, **kwargs)
        queryset = (StudentGroup.objects
                    .filter(pk=kwargs['source_student_group'])
                    .select_related('course__main_branch', 'course__semester',
                                    'course__meta_course'))
        self.student_group = get_object_or_404(queryset)

    def get_permission_object(self) -> StudentGroup:
        return self.student_group

    def post(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=request.POST)
        serializer.is_valid(raise_exception=True)

        destination_student_group = serializer.validated_data['student_group']
        with transaction.atomic():
            StudentGroupService.transfer_students(source=self.student_group,
                                                  destination=destination_student_group,
                                                  student_profiles=serializer.validated_data['ids'])

        msg = f"Студенты успешно перенесены в группу {destination_student_group.name}"
        messages.success(self.request, msg, extra_tags='timeout')
        redirect_to = get_student_groups_url(self.student_group.course)
        return HttpResponseRedirect(redirect_to)
        # return Response(status=status.HTTP_200_OK)
