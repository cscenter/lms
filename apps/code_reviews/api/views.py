from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from code_reviews.api.serializers import StudentAssignmentScoreSerializer
from code_reviews.models import GerritChange
from learning.permissions import EditStudentAssignment


class GerritUpdateReviewGrade(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [EditStudentAssignment, IsAuthenticated]

    def post(self, request, *args, **kwargs):
        queryset = (GerritChange.objects
                    .select_related('student_assignment'))
        if 'change_id' not in request.data:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        change = get_object_or_404(queryset, change_id=request.data['change_id'])
        serializer = StudentAssignmentScoreSerializer(change.student_assignment, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)