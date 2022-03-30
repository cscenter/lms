from typing import Optional

from rest_framework import serializers

from learning.models import StudentAssignment


class StudentAssignmentStatsSerializer(serializers.ModelSerializer):
    sent = serializers.SerializerMethodField()
    first_solution_at = serializers.DateTimeField()
    score = serializers.IntegerField()
    user_id = serializers.PrimaryKeyRelatedField(source="student", read_only=True)

    class Meta:
        model = StudentAssignment
        fields = ("id", "sent", "first_solution_at", "score", "user_id", "status")

    def get_sent(self, obj: StudentAssignment) -> int:
        return int(obj.score is not None or obj.is_submission_received)

    def get_first_solution_at(self, obj: StudentAssignment) -> Optional[str]:
        if not obj.meta or 'stats' not in obj.meta:
            return None
        stats = obj.meta['stats']
        if not stats or 'solutions' not in stats:
            return None
        return stats['solutions']['first']
