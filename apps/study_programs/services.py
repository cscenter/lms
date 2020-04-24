from typing import List

from courses.models import MetaCourse
from core.utils import bucketize
from study_programs.models import StudyProgram


def get_study_programs(meta_course: MetaCourse, filters: List = None):
    """
    Returns study programs grouped by branch where *meta_course*
    is a "core" course.

    "Core" means course is offered as a part of a study program.
    Study program is an academic discipline that offers N groups of courses in
    a particular year and branch. To graduate from the offered academic
    discipline student have to pass at least one course from each group.
    """
    filters = filters or []
    disciplines = (StudyProgram.objects
                   .filter(course_groups__courses=meta_course)
                   .filter(*filters)
                   .select_related('academic_discipline', 'branch')
                   .distinct()
                   .order_by('year'))
    return bucketize(disciplines, key=lambda sp: sp.branch.code)
