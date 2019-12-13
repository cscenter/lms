from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

from core.management import create_default_city_branch_user


class CoreConfig(AppConfig):
    name = 'core'
    verbose_name = _("Core")

    def ready(self):
        post_migrate.connect(create_default_city_branch_user, sender=self)
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
