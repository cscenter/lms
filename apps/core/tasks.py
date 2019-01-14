from django.contrib.contenttypes.models import ContentType
from django_rq import job


@job('default')
def compute_model_field(content_type_id, object_id, compute_field):
    from .mixins import DerivableFieldsMixin

    content_type = ContentType.objects.get_for_id(content_type_id)
    model = content_type.model_class()

    if issubclass(model, DerivableFieldsMixin):
        queryset = model.objects

        prefetch_fields = model.prefetch_before_compute(compute_field)
        if prefetch_fields:
            queryset = queryset.prefetch_related(*prefetch_fields)

        obj = queryset.get(id=object_id)
        obj.compute_fields(compute_field)
