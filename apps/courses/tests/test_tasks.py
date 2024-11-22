from unittest import mock
from django.conf import settings
import pytest

from courses.models import Semester
from courses.tasks import recalculate_invited_priority
from courses.tests.factories import SemesterFactory
from learning.tests.factories import InvitationFactory
from users.tests.factories import InvitedStudentFactory


@pytest.mark.django_db
def test_recalculate_invited_priority(mocker):
    """Email has been generated after registration in yandex contest"""
    current_semester = SemesterFactory.create_current()
    previos_semester = SemesterFactory.create_prev(current_semester)
    preprevios_semester = SemesterFactory.create_prev(previos_semester)
    current_invitation = InvitationFactory(semester=current_semester)
    previos_invitation = InvitationFactory(semester=previos_semester)
    preprevios_invitation = InvitationFactory(semester=preprevios_semester)
    assert Semester.get_current() == current_semester
    previos_user = InvitedStudentFactory()
    previos_profile = previos_user.get_student_profile()
    assert previos_profile.priority == 1000
    with mock.patch('django.utils.timezone.now', return_value=previos_semester.term_pair.starts_at(settings.DEFAULT_TIMEZONE)):
        assert Semester.get_current() == previos_semester
        previos_profile.invitation = preprevios_invitation
        previos_profile.save()
        assert previos_profile.priority == 1300
        previos_profile.invitation = previos_invitation
        previos_profile.save()
        assert previos_profile.priority == 1000
    
    assert previos_profile.priority == 1000
    recalculate_invited_priority(preprevios_semester.id)
    previos_profile.refresh_from_db()
    assert previos_profile.priority == 1000
    recalculate_invited_priority(previos_semester.id)
    previos_profile.refresh_from_db()
    assert previos_profile.priority == 1300
    
    preprevios_user = InvitedStudentFactory()
    preprevios_profile = preprevios_user.get_student_profile()
    preprevios_profile.invitation = preprevios_invitation
    preprevios_profile.save()
    assert preprevios_profile.priority == 1300
    
    with mock.patch('django.utils.timezone.now', return_value=previos_semester.term_pair.starts_at(settings.DEFAULT_TIMEZONE)):
        recalculate_invited_priority(previos_semester.id)
        previos_profile.refresh_from_db()
        assert previos_profile.priority == 1000
    
    current_user = InvitedStudentFactory()
    current_profile = current_user.get_student_profile()
    assert current_profile.priority == 1000
    current_profile.invitation = current_invitation
    current_profile.save()
    assert current_profile.priority == 1000
    
    with mock.patch('django.utils.timezone.now', return_value=preprevios_semester.term_pair.starts_at(settings.DEFAULT_TIMEZONE)):
        recalculate_invited_priority(preprevios_semester.id)
        preprevios_profile.refresh_from_db()
        assert preprevios_profile.priority == 1000
        recalculate_invited_priority(current_semester.id)
        current_profile.refresh_from_db()
        assert current_profile.priority == 1300
        
    recalculate_invited_priority()
    previos_profile.refresh_from_db()
    preprevios_profile.refresh_from_db()
    current_profile.refresh_from_db()
    assert previos_profile.priority == 1300
    assert preprevios_profile.priority == 1300
    assert current_profile.priority == 1000
    
    