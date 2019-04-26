# -*- coding: utf-8 -*-

from django.core.management import BaseCommand
from django.core.management import CommandError

from courses.models import Semester
from learning.projects.models import ProjectStudent, ReportingPeriod, \
    ReportingPeriodKey
from learning.settings import GradeTypes


class Command(BaseCommand):
    help = """
    Set final grade for projects from current term to students who 
    met all the requirements.
    """

    def handle(self, *args, **options):
        """
        Rules applied in order for converting final score to grade:
            score >= ReportingPeriod.score_excellent -> `GradeTypes.excellent`
            score >= ReportingPeriod.score_good -> `GradeTypes.good`
            score >= ReportingPeriod.score_pass -> `GradeTypes.pass`
            score < ReportingPeriod.score_pass -> `GradeTypes.unsatisfactory`
        """
        current_term = Semester.get_current()
        periods = ReportingPeriod.get_final_periods(current_term)
        students = (ProjectStudent.objects
                    .select_related("student", "project")
                    .filter(project__semester_id=current_term.pk,
                            final_grade=GradeTypes.NOT_GRADED))
        processed = 0
        for ps in students:
            if ps.presentation_grade is None:
                continue
            # For external project `supervisor_grade` value is optional
            if not ps.project.is_external and ps.supervisor_grade is None:
                continue
            key = ReportingPeriodKey(branch_code=ps.branch.code,
                                     project_type=ps.project.project_type)
            # FIXME: what if no key in map?
            period = periods[key]
            final_grade = period.score_to_grade(ps)
            result = ProjectStudent.objects.filter(pk=ps.pk).update(
                final_grade=final_grade)
            processed += result
        return str(processed)
