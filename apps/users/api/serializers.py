from rest_framework import serializers

from users.constants import ThumbnailSizes


class PhotoSerializerField(serializers.Field):
    def __init__(self, photo_dimensions, **kwargs):
        assert photo_dimensions in ThumbnailSizes.values
        self.thumbnail_options = kwargs.pop("thumbnail_options", {})
        self.photo_dimensions = photo_dimensions
        super().__init__(**kwargs)

    def get_attribute(self, obj):
        return obj

    def to_internal_value(self, data):
        pass

    def to_representation(self, obj):
        thumbnail_options = {
            "use_stub": True,
            **self.thumbnail_options
        }
        image = obj.get_thumbnail(self.photo_dimensions, **thumbnail_options)
        return image.url
