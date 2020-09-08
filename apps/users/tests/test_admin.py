import pytest

from core.tests.factories import BranchFactory
from courses.models import Semester
from users.admin import StudentProfileForm
from users.models import StudentTypes
from users.tests.factories import StudentProfileFactory


@pytest.mark.django_db
def test_create_different_profile_types_in_one_year_of_admission(client):
    branch = BranchFactory()
    current_year = Semester.get_current().year
    student = StudentProfileFactory(branch=branch,
                                    type=StudentTypes.INVITED,
                                    year_of_admission=current_year)

    new_student_profile = {
        'user': student.user.pk,
        'branch': branch.pk,
        'type': StudentTypes.REGULAR,
        'year_of_admission': current_year
    }
    form = StudentProfileForm(new_student_profile)
    assert form.is_valid()