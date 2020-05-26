import datetime

import pytest

from core.tests.factories import SiteFactory, BranchFactory
from learning.models import GraduateProfile
from learning.settings import StudentStatuses
from users.services import create_graduate_profiles
from users.tests.factories import StudentProfileFactory


@pytest.mark.django_db
def test_create_graduate_profiles():
    site1 = SiteFactory(domain='test.domain')
    site2 = SiteFactory()
    s1, s2, s3 = StudentProfileFactory.create_batch(
        3, status=StudentStatuses.WILL_GRADUATE, branch__site=site1)
    s2.status = StudentStatuses.EXPELLED
    s2.save()
    s4 = StudentProfileFactory(status=StudentStatuses.WILL_GRADUATE,
                               branch__site=site2)
    assert GraduateProfile.objects.count() == 0
    graduated_on = datetime.date(year=2019, month=11, day=3)
    create_graduate_profiles(site1, graduated_on)
    assert GraduateProfile.objects.count() == 2
    assert not GraduateProfile.objects.filter(is_active=True).exists()
    graduate_profiles = list(GraduateProfile.objects.all())
    student_profiles = {g.student_profile_id for g in graduate_profiles}
    assert s1.pk in student_profiles
    assert s3.pk in student_profiles
    assert graduate_profiles[0].graduated_on == graduated_on
