from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from courses.models import Semester
from learning.models import EnrollmentPeriod


@receiver(post_save, sender=Semester)
def create_enrollment_period_for_compsciclub_ru(sender, instance: Semester,
                                                created, *args, **kwargs):
    """Side effect for compsciclub.ru creates predefined enrollment period"""
    if not created:
        return
    ends_on = instance.ends_at.date()
    EnrollmentPeriod.objects.get_or_create(site_id=settings.CLUB_SITE_ID,
                                           semester=instance,
                                           defaults={"ends_on": ends_on})
