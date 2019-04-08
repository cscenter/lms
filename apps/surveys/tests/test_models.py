from datetime import timedelta

import pytest

from core.timezone import now_local
from courses.tests.factories import CourseFactory
from learning.settings import Branches
from surveys.constants import STATUS_PUBLISHED, STATUS_DRAFT
from surveys.models import CourseSurvey, Field, FieldChoice
from surveys.tests.factories import CourseSurveyFactory


@pytest.mark.django_db
def test_course_survey_is_active():
    course = CourseFactory(city_id=Branches.SPB)
    today = now_local(course.get_city_timezone())
    cs = CourseSurveyFactory(course=course, publish_at=None, expire_at=None)
    assert cs.is_active
    cs.publish_at = today + timedelta(hours=1)
    assert not cs.is_active
    cs.publish_at = None
    cs.publish_at = today - timedelta(hours=1)
    assert cs.is_active
    cs.publish_at = None
    cs.expire_at = today + timedelta(hours=1)
    assert cs.is_active
    cs.expire_at = today - timedelta(hours=1)
    assert not cs.is_active


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


@pytest.mark.django_db
def test_final_survey_builder_field_label():
    course = CourseFactory(city_id=Branches.SPB)
    cs = CourseSurveyFactory(course=course, type=CourseSurvey.MIDDLE,
                             # Create form with a form builder
                             form_id=None)
    default_label = "Что вы думаете о том, как проходят очные лекции?"
    assert Field.objects.filter(form_id=cs.form_id, label=default_label).exists()
    cs = CourseSurveyFactory(course=course, type=CourseSurvey.FINAL,
                             # Create form with a form builder
                             form_id=None)
    assert not Field.objects.filter(form_id=cs.form_id, label=default_label).exists()
    final_survey_label = "Что вы думаете о том, как проходили очные лекции?"
    assert Field.objects.filter(form_id=cs.form_id, label=final_survey_label).exists()


@pytest.mark.django_db
def test_final_survey_builder_field_choice_label():
    course = CourseFactory(city_id=Branches.SPB)
    cs = CourseSurveyFactory(course=course, type=CourseSurvey.MIDDLE,
                             # Create form with a form builder
                             form_id=None)
    label = "Что вы думаете о том, как проходят очные лекции?"
    assert Field.objects.filter(form_id=cs.form_id, label=label).exists()
    field = Field.objects.get(form_id=cs.form_id, label=label)
    assert FieldChoice.objects.filter(field_id=field.pk, label="Материал разбирается слишком быстро").exists()
    cs = CourseSurveyFactory(course=course, type=CourseSurvey.FINAL,
                             # Create form with a form builder
                             form_id=None)
    label = "Что вы думаете о том, как проходили очные лекции?"
    assert Field.objects.filter(form_id=cs.form_id, label=label).exists()
    field = Field.objects.get(form_id=cs.form_id, label=label)
    assert not FieldChoice.objects.filter(field_id=field.pk, label="Материал разбирается слишком быстро").exists()
    assert FieldChoice.objects.filter(field_id=field.pk, label="Материал разбирался слишком быстро").exists()
    assert FieldChoice.objects.filter(field_id=field.pk, label="Тематика и чтение курса мне понравились, и я хочу продолжить изучение материала").exists()
