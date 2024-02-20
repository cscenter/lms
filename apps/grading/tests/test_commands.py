from io import StringIO

import pytest

from django.core import management

from courses.constants import SemesterTypes
from courses.tests.factories import SemesterFactory
from learning.settings import GradeTypes
from learning.tests.factories import EnrollmentFactory
from core.tests.factories import SiteFactory

@pytest.mark.django_db
@pytest.mark.parametrize("prev_sem_flag, enrollment_2018_grade, enrollment_2020_grade, enrollment_2022_grade,"
                         "enrollment_2023_grade, current_grade",
                         [(False, GradeTypes.NOT_GRADED, GradeTypes.NOT_GRADED, GradeTypes.NOT_GRADED,
                           GradeTypes.NOT_GRADED, GradeTypes.UNSATISFACTORY),
                          (True, GradeTypes.NOT_GRADED, GradeTypes.UNSATISFACTORY, GradeTypes.UNSATISFACTORY,
                           GradeTypes.UNSATISFACTORY, GradeTypes.NOT_GRADED)])
def test_autofail_ungraded(settings, prev_sem_flag, enrollment_2018_grade, enrollment_2020_grade, enrollment_2022_grade,
                           enrollment_2023_grade, current_grade):
    settings.LANGUAGE_CODE = 'ru'
    term_2018_autumn = SemesterFactory(year=2018, type=SemesterTypes.AUTUMN)
    term_2020_autumn = SemesterFactory(year=2020, type=SemesterTypes.AUTUMN)
    term_2022_spring = SemesterFactory(year=2022, type=SemesterTypes.SPRING)
    term_2023_autumn = SemesterFactory(year=2023, type=SemesterTypes.AUTUMN)
    current_term = SemesterFactory.create_current()
    site = SiteFactory()
    out = StringIO()

    enrollment_2018 = EnrollmentFactory(course__semester=term_2018_autumn)
    enrollment_2020 = EnrollmentFactory(course__semester=term_2020_autumn)
    enrollment_2022 = EnrollmentFactory(course__semester=term_2022_spring)
    enrollment_2023 = EnrollmentFactory(course__semester=term_2023_autumn)
    current_enrollment = EnrollmentFactory(course__semester=current_term)

    assert enrollment_2018.grade == GradeTypes.NOT_GRADED
    assert enrollment_2020.grade == GradeTypes.NOT_GRADED
    assert enrollment_2022.grade == GradeTypes.NOT_GRADED
    assert enrollment_2023.grade == GradeTypes.NOT_GRADED
    assert current_enrollment.grade == GradeTypes.NOT_GRADED

    management.call_command("autofail_ungraded", site, prev_sem=prev_sem_flag, stdout=out)

    assert out.getvalue().strip() != "0"

    enrollment_2018.refresh_from_db()
    enrollment_2020.refresh_from_db()
    enrollment_2022.refresh_from_db()
    enrollment_2023.refresh_from_db()
    current_enrollment.refresh_from_db()

    assert enrollment_2018.grade == enrollment_2018_grade
    assert enrollment_2020.grade == enrollment_2020_grade
    assert enrollment_2022.grade == enrollment_2022_grade
    assert enrollment_2023.grade == enrollment_2023_grade
    assert current_enrollment.grade == current_grade
