import json

from django.conf import settings
from rest_framework.renderers import BrowsableAPIRenderer
from rest_pandas import PandasCSVRenderer, PandasJSONRenderer


class PandasListIndentJSONRenderer(PandasJSONRenderer):
    def get_output(self):
        value = self.output.getvalue()
        return json.dumps(json.loads(value), indent=4)


if settings.DEBUG:
    _PandasJSONRenderer = PandasListIndentJSONRenderer
else:
    _PandasJSONRenderer = PandasJSONRenderer


class ListRenderersMixin:
    renderer_classes = [BrowsableAPIRenderer, _PandasJSONRenderer,
                        PandasCSVRenderer]
