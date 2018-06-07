from rest_framework import serializers

from users.models import CSCUser


class AlumniSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk")
    name = serializers.SerializerMethodField()
    photo = serializers.SerializerMethodField()
    year = serializers.IntegerField(source="graduation_year")
    city = serializers.CharField(source="city_id")
    areas = serializers.PrimaryKeyRelatedField(many=True,
                                               read_only=True,
                                               source="areas_of_study")

    class Meta:
        model = CSCUser
        fields = ('id', 'name', 'year', 'city', 'photo', 'areas')

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_photo(self, obj):
        # TODO: move size to settings?
        image = obj.get_thumbnail("170x238", use_stub=False)
        if image:
            return image.url
        else:
            return None
