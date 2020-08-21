# -*- coding: utf-8 -*-
import logging

from django.core.management import BaseCommand
from django.core.management import CommandError

from courses.models import Semester
from projects.models import ProjectStudent, ReportingPeriod, \
    ReportingPeriodKey
from projects.constants import ProjectGradeTypes


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """
    Set final grade for projects from current term to students who 
    met all the requirements.
    """

    def handle(self, *args, **options):
        """
        Rules applied in order for converting final score to grade:
            score >= ReportingPeriod.score_excellent -> `ProjectGradeTypes.excellent`
            score >= ReportingPeriod.score_good -> `ProjectGradeTypes.good`
            score >= ReportingPeriod.score_pass -> `ProjectGradeTypes.pass`
            score < ReportingPeriod.score_pass -> `ProjectGradeTypes.unsatisfactory`
        """
        current_term = Semester.get_current()
        periods = ReportingPeriod.get_final_periods(current_term)
        if not periods:
            raise CommandError(f"Для семестра '{current_term}' не "
                               f"найдены отчетные периоды.")
        # Make sure all final periods have score settings
        for period in periods.values():
            attrs = ('score_excellent', 'score_good', 'score_pass')
            if any(getattr(period, attr) is None for attr in attrs):
                raise CommandError(f"Для отчетного периода '{period}' не "
                                   f"выставлены настройки с оценками.")
        students = (ProjectStudent.objects
                    .select_related("student", "project")
                    .filter(project__semester_id=current_term.pk,
                            final_grade=ProjectGradeTypes.NOT_GRADED))
        processed = 0
        graded = 0
        for ps in students:
            processed += 1
            if ps.presentation_grade is None:
                continue
            # For external project `supervisor_grade` value is optional
            if not ps.project.is_external and ps.supervisor_grade is None:
                continue
            key = ReportingPeriodKey(branch_code=ps.student.branch.code,
                                     project_type=ps.project.project_type)
            if key not in periods:
                logger.warning(f"Не найден отчетный период. "
                               f"Семестр {current_term}, "
                               f"отделение: {ps.student.branch}, "
                               f"тип проекта: {ps.project.project_type}")
                continue
            period = periods[key]
            final_grade = period.score_to_grade(ps.total_score, ps.project)
            result = ProjectStudent.objects.filter(pk=ps.pk).update(
                final_grade=final_grade)
            graded += result
        return str(graded)
