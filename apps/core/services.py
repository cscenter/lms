from operator import attrgetter
from typing import TYPE_CHECKING, Any

from django.db import transaction
from django.db.models import signals, sql
from django.utils import timezone

from core.db.models import SoftDeletionModel

if TYPE_CHECKING:
    # TODO: Remove once Collector in django-stubs has attribute types.
    Collector = Any
else:
    from django.db.models.deletion import Collector


class SoftDeleteService:
    """
    Supports `deleted_at` field value update for models that implement
    soft-delete interface by subclassing `SoftDeletionModel`.
    """
    def __init__(self, using, keep_parents=False):
        self.using = using
        self.keep_parents = keep_parents

    def delete(self, objects):
        collector = Collector(using=self.using)
        collector.collect(objects, keep_parents=self.keep_parents)
        now = timezone.now()
        self.__update_models(collector, now)

    def restore(self, objects):
        collector = Collector(using=self.using)
        collector.collect(objects, keep_parents=self.keep_parents)
        self.__update_models(collector, None)

    def __update_models(self, collector: Collector, deleted_at_value):
        # sort instance collections
        for model, instances in collector.data.items():
            if not issubclass(model, SoftDeletionModel):
                continue
            collector.data[model] = sorted(instances, key=attrgetter("pk"))

        # if possible, bring the models in an order suitable for databases that
        # don't support transactions or cannot defer constraint checks until the
        # end of a transaction.
        collector.sort()

        with transaction.atomic(using=collector.using, savepoint=False):
            # send pre_delete signals
            for model, obj in collector.instances_with_model():
                if not issubclass(model, SoftDeletionModel):
                    continue
                if not model._meta.auto_created:
                    signals.pre_delete.send(
                        sender=model, instance=obj, using=collector.using
                    )

            # Update fast deletes
            for qs in collector.fast_deletes:
                if not issubclass(qs.model, SoftDeletionModel):
                    continue
                qs.update(deleted_at=deleted_at_value)

            # reverse instance collections
            for instances in collector.data.values():
                instances.reverse()

            # Update instances
            for model, instances in collector.data.items():
                if not issubclass(model, SoftDeletionModel):
                    continue
                query = sql.UpdateQuery(model)
                pk_list = [obj.pk for obj in instances]
                query.update_batch(pk_list,
                                   {"deleted_at": deleted_at_value},
                                   collector.using)
                for obj in instances:
                    obj.deleted_at = deleted_at_value

                if not model._meta.auto_created:
                    for obj in instances:
                        signals.post_delete.send(
                            sender=model, instance=obj, using=collector.using
                        )
