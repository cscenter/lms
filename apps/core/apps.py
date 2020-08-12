from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    name = 'core'
    verbose_name = _("Core")

    def ready(self):
        from rest_framework.serializers import ModelSerializer
        # Register checks
        from . import checks
        # Register custom lookups
        from .db import lookups
        # Update Django Rest Framework serializer mappings
        from core.db.models import ScoreField
        from core.api import fields
        field_mapping = ModelSerializer.serializer_field_mapping
        field_mapping.update({
            ScoreField: fields.ScoreField
        })
