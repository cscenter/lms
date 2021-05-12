import pytest

from django.db import connection, models, router

from core.db.models import SoftDeletionModel
from core.services import SoftDeleteService


@pytest.mark.django_db
def test_soft_delete_collector():
    class Parent(SoftDeletionModel, models.Model):
        pass

    class SoftChild(SoftDeletionModel, models.Model):
        parent = models.ForeignKey(Parent, on_delete=models.CASCADE)

    class SoftSoftChild(SoftDeletionModel, models.Model):
        parent = models.ForeignKey(SoftChild, on_delete=models.CASCADE)

    class HardSoftChild(models.Model):
        parent = models.ForeignKey(SoftChild, on_delete=models.CASCADE)

    class HardChild(models.Model):
        parent = models.ForeignKey(Parent, on_delete=models.CASCADE,
                                   related_name='hard_child')

    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(Parent)
        schema_editor.create_model(SoftChild)
        schema_editor.create_model(SoftSoftChild)
        schema_editor.create_model(HardSoftChild)
        schema_editor.create_model(HardChild)
    p = Parent()
    p.save()
    soft_child = SoftChild(parent=p)
    soft_child.save()
    SoftSoftChild(parent=soft_child).save()
    HardSoftChild(parent=soft_child).save()
    hard_child = HardChild(parent=p)
    hard_child.save()
    using = router.db_for_write(Parent, instance=p)
    SoftDeleteService(using).delete([p])
    assert p.pk is not None, "Without pk it's impossible to call .restore()"
    assert p.is_deleted
    assert Parent.objects.count() == 0
    assert Parent.trash.count() == 1
    assert SoftChild.objects.count() == 0
    assert HardChild.objects.count() == 1
    assert SoftSoftChild.objects.count() == 0
    assert SoftSoftChild.trash.count() == 1
    assert HardSoftChild.objects.count() == 1
    SoftDeleteService(using).restore([p])
    assert not p.is_deleted
    assert Parent.objects.count() == 1
    assert Parent.trash.count() == 0
    assert SoftSoftChild.objects.count() == 1
    assert SoftSoftChild.trash.count() == 0
    assert HardSoftChild.objects.count() == 1
    # All tmp models should be automatically removed
