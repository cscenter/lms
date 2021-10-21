import pytest
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED

from api.authentication import TokenAuthentication
from api.views import APIBaseView
from auth.mixins import RolePermissionRequiredMixin
from code_reviews.gerrit.tasks import import_gerrit_code_review_score
from learning.permissions import EditStudentAssignment


class GerritCommentAddedWebhook(RolePermissionRequiredMixin, APIBaseView):
    """
    Adds task to the queue for updating personal assignment score based
    on the code review results.
    """
    authentication_classes = [TokenAuthentication]
    # Only model-level permissions will be checked since permission object is None
    permission_classes = [EditStudentAssignment]

    class InputSerializer(serializers.Serializer):
        change_id = serializers.CharField()
        username = serializers.CharField()
        score_old = serializers.IntegerField()
        score_new = serializers.IntegerField()

    def post(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = import_gerrit_code_review_score.delay(**serializer.validated_data)
        payload = {
            "id": task.id,
        }
        return Response(data=payload, status=HTTP_201_CREATED)
