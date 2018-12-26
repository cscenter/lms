import pytest

from courses.factories import CourseNewsFactory


@pytest.mark.django_db
def test_news_get_city_timezone(settings):
    news = CourseNewsFactory(course__city_id='nsk')
    assert news.get_city_timezone() == settings.TIME_ZONES['nsk']
    news.course.city_id = 'spb'
    news.course.save()
    news.refresh_from_db()
    assert news.get_city_timezone() == settings.TIME_ZONES['spb']