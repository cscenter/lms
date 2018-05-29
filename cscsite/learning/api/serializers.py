from rest_framework import serializers

from users.models import CSCUser


class AlumniSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    year = serializers.IntegerField(source="graduation_year")
    city = serializers.CharField(source="city_id")
    areas = serializers.PrimaryKeyRelatedField(many=True,
                                               read_only=True,
                                               source="areas_of_study")

    class Meta:
        model = CSCUser
        fields = ('name', 'year', 'city', 'areas')

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
