import pytest

from core.tests.factories import BranchFactory
from courses.tests.factories import SemesterFactory, CourseFactory, CourseClassFactory
from learning.services import get_classes
from learning.settings import Branches


@pytest.mark.django_db
def test_course_class_manager_in_branches_for_club(client, settings):
    """
    Сlub students should only see classes from any courses that:
      * are hosted by the current club branch
      * were shared with the current club branch
    """
    current_semester = SemesterFactory.create_current()
    branch_center = BranchFactory(code=Branches.SPB,
                                  site__domain=settings.ANOTHER_DOMAIN)
    branch_club = BranchFactory(code=Branches.SPB)
    co_center = CourseFactory.create(semester=current_semester,
                                     main_branch=branch_center)
    co_spb = CourseFactory.create(semester=current_semester)
    co_kzn = CourseFactory.create(semester=current_semester,
                                  main_branch__code="kzn")
    cc_center = CourseClassFactory(course=co_center)
    cc_spb = CourseClassFactory(course=co_spb)
    cc_kzn = CourseClassFactory(course=co_kzn)

    classes = list(get_classes(branch_list=[branch_club]))
    assert len(classes) == 1
    assert cc_center not in classes
    assert cc_spb in classes
    assert cc_kzn not in classes

    # Share center course with the club branch
    co_center.branches.add(branch_club)
    classes = list(get_classes(branch_list=[branch_club]))
    assert len(classes) == 2
    assert cc_center in classes
