from rest_framework import serializers


class PhotoSerializerField(serializers.Field):
    def __init__(self, photo_dimensions, **kwargs):
        self.photo_dimensions = photo_dimensions
        super().__init__(**kwargs)

    def get_attribute(self, obj):
        return obj

    def to_internal_value(self, data):
        pass

    def to_representation(self, obj):
        # TODO: get dimensions from map and throw warning if unspecified value was passed
        image = obj.get_thumbnail(self.photo_dimensions, use_stub=False)
        if image:
            return image.url
        else:
            return None