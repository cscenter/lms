from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    name = 'core'
    verbose_name = _("Core")

    def ready(self):
        # Register checks
        from . import checks  # isort:skip  pylint: disable=unused-import
        # Register signals
        from . import signals  # isort:skip  pylint: disable=unused-import
        # Register custom lookups
        from .db import lookups  # isort:skip  pylint: disable=unused-import
        # Update Django Rest Framework serializer mappings
        from rest_framework.serializers import ModelSerializer  # isort:skip
        from core.api import fields  # isort:skip
        from core.db.fields import ScoreField  # isort:skip
        field_mapping = ModelSerializer.serializer_field_mapping
        field_mapping.update({
            # TODO: mypy should be able to type check this. Investigate and remove the ignore.
            ScoreField: fields.ScoreField  # type: ignore[dict-item]
        })


class CustomAdminConfig(AdminConfig):
    default_site = 'core.admin_site.BaseAdminSite'
