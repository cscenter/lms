import pytest

from courses.models import CourseGroupModes, StudentGroupTypes
from courses.tests.factories import CourseFactory
from learning.models import StudentGroup
from learning.teaching.utils import get_create_student_group_url
from users.tests.factories import TeacherFactory


@pytest.mark.django_db
def test_student_group_view_create(client):
    teacher = TeacherFactory()
    client.login(teacher)
    course = CourseFactory(teachers=[teacher], group_mode=CourseGroupModes.MANUAL)
    assert StudentGroup.objects.filter(course=course).count() == 0
    create_url = get_create_student_group_url(course)
    form_data = {
        'name': 'Test Student Group Name',
    }
    response = client.post(create_url, form_data)
    assert response.status_code == 302
    assert StudentGroup.objects.filter(course=course).count() == 1
    student_group = StudentGroup.objects.filter(course=course).get()
    assert student_group.name == form_data['name']
    assert student_group.type == StudentGroupTypes.MANUAL


