from django.conf import settings
from pandas import DataFrame
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_pandas import PandasCSVRenderer, PandasJSONRenderer


class PandasListIndentJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        if not isinstance(data, DataFrame):
            raise Exception(
                "Response data is a %s, not a DataFrame!" % type(data)
            )
        # FIXME: this solution is unordered! But PandasJSONRenderer not indented
        return super().render(data.to_dict(orient='records'),
                              accepted_media_type,
                              renderer_context)


if settings.DEBUG:
    _PandasJSONRenderer = PandasListIndentJSONRenderer
else:
    # Default orient is `records` for output JSON
    _PandasJSONRenderer = PandasJSONRenderer


class ListRenderersMixin:
    renderer_classes = [BrowsableAPIRenderer, _PandasJSONRenderer,
                        PandasCSVRenderer]
