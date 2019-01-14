# -*- coding: utf-8 -*-

from django.core.management import BaseCommand
from django.core.management import CommandError

from courses.models import Semester
from learning.projects.models import ProjectStudent
from learning.settings import GradeTypes


class Command(BaseCommand):
    help = """
    Calculates final grade for student projects without final grade value.
    """

    def handle(self, *args, **options):
        """
        Scheme:
            unsatisfactory [PASS BORDER] pass [GOOD BORDER] good [EXCELLENT BORDER]
        Rules:
            score >= [EXCELLENT BORDER] -> `GradeTypes.excellent`
            [GOOD BORDER] <= score < [EXCELLENT BORDER] -> `GradeTypes.good`
            [PASS BORDER] <= score < [GOOD BORDER] -> `GradeTypes.pass`
            score < [PASS BORDER] -> `GradeTypes.unsatisfactory`
        """
        current_term = Semester.get_current()
        # Validate term settings
        project_settings = [
            current_term.projects_grade_excellent,
            current_term.projects_grade_good,
            current_term.projects_grade_pass,
        ]
        if any(p is None for p in project_settings):
            raise CommandError("Make sure you provided all necessary settings"
                               " for current term.")
        if max(*project_settings) != current_term.projects_grade_excellent:
            raise CommandError("Border for `excellent` grade must be "
                               "the highest.")
        if min(*project_settings) != current_term.projects_grade_pass:
            raise CommandError("Border for `pass` grade must be the lowest.")

        students = (ProjectStudent.objects
                    .select_related("report", "project")
                    .filter(project__semester_id=current_term.pk,
                            final_grade=GradeTypes.NOT_GRADED))
        processed = 0
        for ps in students:
            total_score = ps.total_score
            is_external = ps.project.is_external
            if ps.presentation_grade is None:
                continue
            # For external project `supervisor_grade` value is optional.
            if not is_external and ps.supervisor_grade is None:
                continue
            # Select the appropriate grade
            if total_score >= current_term.projects_grade_excellent:
                final_grade = GradeTypes.EXCELLENT
            elif total_score >= current_term.projects_grade_good:
                final_grade = GradeTypes.GOOD
            elif total_score >= current_term.projects_grade_pass:
                final_grade = GradeTypes.CREDIT
            else:
                final_grade = GradeTypes.UNSATISFACTORY
            # For external project we have binary grading policy.
            if is_external and total_score >= current_term.projects_grade_pass:
                final_grade = GradeTypes.CREDIT

            result = ProjectStudent.objects.filter(pk=ps.pk).update(
                final_grade=final_grade)
            processed += result
        return str(processed)
