from courses.models import Course

from django.db import models
from django.db.models.signals import m2m_changed
from django.dispatch import receiver


@receiver(m2m_changed, sender=Course.additional_branches.through)
def additional_branches_changed(sender, instance, action, **kwargs):
    """
    Removes course primary branch from additional branches to avoid
    duplicates in `Course.objects.could_enroll_in` method
    """
    if action == 'pre_add':
        pk_set = kwargs.pop('pk_set', None)
        if instance.branch_id in pk_set:
            pk_set.remove(instance.branch_id)
