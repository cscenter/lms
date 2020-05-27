from rest_framework import serializers

from learning.api.serializers import StudentSerializer


class StudentSearchSerializer(StudentSerializer):
    pk = serializers.IntegerField(source="user_id")
    short_name = serializers.SerializerMethodField()

    class Meta(StudentSerializer.Meta):
        fields = ('short_name', 'pk')

    def get_short_name(self, student_profile):
        return student_profile.user.get_short_name()
