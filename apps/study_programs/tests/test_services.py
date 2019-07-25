import pytest
from django.db.models import Q

from courses.tests.factories import MetaCourseFactory, CourseFactory
from study_programs.services import get_study_programs
from study_programs.tests.factories import StudyProgramFactory, \
    StudyProgramCourseGroupFactory, AcademicDisciplineFactory


@pytest.mark.django_db
def test_get_study_programs():
    ad1 = AcademicDisciplineFactory()
    ad2 = AcademicDisciplineFactory()
    sp1 = StudyProgramFactory(is_active=True, academic_discipline=ad1)
    sp2 = StudyProgramFactory(is_active=True, academic_discipline=ad2)
    c1, c2, c3 = MetaCourseFactory.create_batch(3)
    StudyProgramCourseGroupFactory(study_program=sp1, courses=[c1, c2])
    StudyProgramCourseGroupFactory(study_program=sp2, courses=[c2, c3])
    study_programs = get_study_programs(c1)
    assert list(study_programs) == [sp1.branch.code]
    assert len(study_programs[sp1.branch.code]) == 1
    assert study_programs[sp1.branch.code][0] == sp1
    assert len(get_study_programs(c2)) == 2
    assert len(get_study_programs(c2, filters=[Q(is_active=False)])) == 0
