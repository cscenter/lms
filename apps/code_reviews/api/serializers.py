from rest_framework import serializers

from learning.models import StudentAssignment


class StudentAssignmentScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAssignment
        fields = ('score',)
