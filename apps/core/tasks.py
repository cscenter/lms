from django_rq import job

from django.contrib.contenttypes.models import ContentType


@job('default')
def compute_model_fields(content_type_id, object_id, compute_fields):
    from core.db.mixins import DerivableFieldsMixin

    content_type = ContentType.objects.get_for_id(content_type_id)
    model = content_type.model_class()

    if model is None:
        return

    if issubclass(model, DerivableFieldsMixin):
        queryset = model._base_manager  # type: ignore

        prefetch_fields = model.prefetch_before_compute(*compute_fields)
        if prefetch_fields:
            queryset = queryset.prefetch_related(*prefetch_fields)

        obj = queryset.get(id=object_id)
        obj.compute_fields(*compute_fields)
