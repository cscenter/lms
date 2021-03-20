from rest_framework import serializers

from learning.models import StudentAssignment


class StudentAssignmentsSerializer(serializers.ModelSerializer):
    sent = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    first_student_comment_at = serializers.DateTimeField()
    score = serializers.IntegerField()
    user_id = serializers.PrimaryKeyRelatedField(source="student", read_only=True)

    class Meta:
        model = StudentAssignment
        fields = ("id", "sent", "first_student_comment_at", "score", "user_id",
                  "state")

    def get_state(self, obj):
        return obj.state.value

    def get_sent(self, obj):
        """
        Let's say user passed assignment if he sent comment or has score
        """
        # FIXME: rewrite with `submission_is_received`? Check what about
        #  offline assignments here.
        return int(obj.score is not None or
                   obj.submission_is_received != StudentAssignment.CommentAuthorTypes.NOBODY)
