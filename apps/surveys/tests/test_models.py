from datetime import timedelta

import pytest

from core.timezone import now_local
from courses.tests.factories import CourseFactory
from learning.settings import Branches
from surveys.constants import STATUS_PUBLISHED, STATUS_DRAFT
from surveys.models import CourseSurvey
from surveys.tests.factories import CourseSurveyFactory


@pytest.mark.django_db
def test_get_active():
    course = CourseFactory(city_id=Branches.SPB)
    active_cs = CourseSurvey.get_active(course)
    assert active_cs is None
    cs = CourseSurveyFactory(course=course, expire_at=None,
                             form__status=STATUS_PUBLISHED)
    active_cs = CourseSurvey.get_active(course)
    assert active_cs == cs
    today = now_local(course.get_city_timezone())
    cs.expire_at = today + timedelta(days=1)
    cs.save()
    active_cs = CourseSurvey.get_active(course)
    assert active_cs == cs
    cs.expire_at = today - timedelta(days=2)
    cs.save()
    active_cs = CourseSurvey.get_active(course)
    assert active_cs is None
    # Make sure we get the latest active survey link
    cs.expire_at = today + timedelta(days=2)
    cs.save()
    cs2 = CourseSurveyFactory(course=course,
                              expire_at=today + timedelta(days=3),
                              form__status=STATUS_PUBLISHED)
    active_cs = CourseSurvey.get_active(course)
    assert active_cs == cs2
    cs2.form.status = STATUS_DRAFT
    cs2.form.save()
    active_cs = CourseSurvey.get_active(course)
    assert active_cs == cs
    cs.publish_at = today + timedelta(days=1)
    cs.save()
    active_cs = CourseSurvey.get_active(course)
    assert active_cs is None

