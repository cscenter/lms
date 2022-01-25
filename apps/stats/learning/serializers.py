from rest_framework import serializers

from learning.models import StudentAssignment


class StudentAssignmentStatsSerializer(serializers.ModelSerializer):
    sent = serializers.SerializerMethodField()
    first_student_comment_at = serializers.DateTimeField()
    score = serializers.IntegerField()
    user_id = serializers.PrimaryKeyRelatedField(source="student", read_only=True)

    class Meta:
        model = StudentAssignment
        fields = ("id", "sent", "first_student_comment_at", "score", "user_id",
                  "status")

    def get_sent(self, obj: StudentAssignment) -> int:
        return int(obj.score is not None or obj.is_submission_received)
