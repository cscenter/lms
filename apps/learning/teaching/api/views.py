from typing import Any

from djangorestframework_camel_case.render import (
    CamelCaseBrowsableAPIRenderer, CamelCaseJSONRenderer
)
from rest_framework import serializers, status
from rest_framework.response import Response

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404

from api.views import APIBaseView
from auth.mixins import RolePermissionRequiredMixin
from core.http import AuthenticatedHttpRequest, HttpRequest
from learning.api.serializers import UserSerializer
from learning.models import AssignmentScoreAuditLog, StudentAssignment, StudentGroup
from learning.permissions import EditStudentAssignment, UpdateStudentGroup
from learning.services import StudentGroupService
from learning.settings import AssignmentScoreUpdateSource
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


class PersonalAssignmentScoreAuditLogView(RolePermissionRequiredMixin, APIBaseView):
    student_assignment: StudentAssignment
    permission_classes = [EditStudentAssignment]
    renderer_classes = (CamelCaseJSONRenderer, CamelCaseBrowsableAPIRenderer)

    class OutputSerializer(serializers.ModelSerializer):
        changed_by = UserSerializer(fields=('id', 'first_name', 'last_name', 'patronymic', 'username'))

        class Meta:
            model = AssignmentScoreAuditLog
            fields = ('created_at', 'changed_by', 'score_old', 'score_new', 'source')

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any):
        super().setup(request, *args, **kwargs)
        queryset = (StudentAssignment.objects
                    .filter(pk=kwargs['student_assignment_id'])
                    .select_related('assignment__course'))
        self.student_assignment = get_object_or_404(queryset)

    def get_permission_object(self) -> StudentAssignment:
        return self.student_assignment

    def get(self, request: AuthenticatedHttpRequest, **kwargs) -> Response:
        audit_log = (AssignmentScoreAuditLog.objects
                     .filter(student_assignment=self.student_assignment)
                     .order_by('-created_at'))
        data = self.OutputSerializer(audit_log, many=True).data
        return Response(status=status.HTTP_200_OK, data={
            "edges": data,
            "sources": {k: v for k, v in AssignmentScoreUpdateSource.choices}
        })
