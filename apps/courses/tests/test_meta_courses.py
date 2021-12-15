import factory
import pytest

from auth.mixins import PermissionRequiredMixin
from courses.models import MetaCourse
from courses.permissions import EditMetaCourse
from courses.tests.factories import CourseFactory, MetaCourseFactory
from users.tests.factories import CuratorFactory, UserFactory


@pytest.mark.django_db
def test_meta_course_detail(client, assert_login_redirect):
    mc = MetaCourseFactory.create()
    co1 = CourseFactory(meta_course=mc)
    co2 = CourseFactory(meta_course=mc)
    assert_login_redirect(mc.get_absolute_url())
    client.login(UserFactory())
    response = client.get(mc.get_absolute_url())
    assert response.status_code == 200
    assert mc.name.encode() in response.content
    assert mc.description.encode() in response.content


@pytest.mark.django_db
def test_meta_course_update_security(client, lms_resolver,
                                     assert_login_redirect):
    from auth.permissions import perm_registry
    meta_course = MetaCourseFactory()
    update_url = meta_course.get_update_url()
    resolver = lms_resolver(update_url)
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == EditMetaCourse.name
    assert resolver.func.view_class.permission_required in perm_registry
    assert_login_redirect(update_url, method='get')
    curator = CuratorFactory()
    client.login(curator)
    response = client.get(update_url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_meta_course_update(client, assert_redirect):
    curator = CuratorFactory()
    meta_course = MetaCourseFactory()
    client.login(curator)
    form = factory.build(dict, FACTORY_CLASS=MetaCourseFactory)
    form.update({
        'name_ru': "foobar",
        'description_ru': "foobar",
    })
    response = client.post(meta_course.get_update_url(), form)
    assert response.status_code == 302
    assert MetaCourse.objects.get(pk=meta_course.pk).name_ru == "foobar"
