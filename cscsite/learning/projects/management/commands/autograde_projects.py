# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from datetime import timedelta
from django.apps import apps
from django.core.management import BaseCommand
from django.core.management import CommandError
from django.core.urlresolvers import reverse
from django.db import transaction
from django.utils.timezone import now

from learning.models import Semester
from learning.projects.models import ProjectStudent
from learning.settings import GRADES
from notifications import types
from notifications.models import Notification
from notifications.signals import notify


class Command(BaseCommand):
    help = """
    Calculate final grade for each student project (without grade) based
    on `total_score` of the student's work, type of the project and settings
    from Semester model.
    """

    def handle(self, *args, **options):
        """
        Principal scheme:
            unsatisfactory [PASS BORDER] pass [GOOD BORDER] good [EXCELLENT BORDER]
        Rules:
            score >= [EXCELLENT BORDER] -> `GRADES.excellent`
            [GOOD BORDER] <= score < [EXCELLENT BORDER] -> `GRADES.good`
            [PASS BORDER] <= score < [GOOD BORDER] -> `GRADES.pass`
            score < [PASS BORDER] -> `GRADES.unsatisfactory`
        """
        current_term = Semester.get_current()
        # Validate term settings
        project_settings = [
            current_term.projects_grade_excellent,
            current_term.projects_grade_good,
            current_term.projects_grade_pass,
        ]
        if any(p is None for p in project_settings):
            raise CommandError("Make sure you provide all necessary settings"
                               " for provided term.")
        if max(*project_settings) != current_term.projects_grade_excellent:
            raise CommandError("Border for `excellent` grade must be "
                               "the highest.")
        if min(*project_settings) != current_term.projects_grade_pass:
            raise CommandError("Border for `pass` grade must be the lowest.")

        students = (ProjectStudent.objects
                    .select_related("report", "project__is_external")
                    .filter(project__semester_id=current_term.pk,
                            final_grade=GRADES.not_graded))
        for ps in students:
            total_score = ps.total_score
            is_external = ps.project.is_external
            # We process models without grade only, for external project
            # `supervisor_grade` value is optional.
            if ps.presentation_grade is None:
                continue
            if not is_external and ps.supervisor_grade is None:
                continue
            # Calculate final grade based on logic above
            if total_score >= current_term.projects_grade_excellent:
                final_grade = GRADES.excellent
            elif total_score >= current_term.projects_grade_good:
                final_grade = GRADES.good
            elif total_score >= current_term.projects_grade_pass:
                final_grade = getattr(GRADES, "pass")
            else:
                final_grade = GRADES.unsatisfactory
            # For external project we have binary grading policy.
            if is_external and total_score >= current_term.projects_grade_pass:
                final_grade = getattr(GRADES, "pass")
            # Update query
            ProjectStudent.objects.filter(pk=ps.pk).update(
                final_grade=final_grade)
