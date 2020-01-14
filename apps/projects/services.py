from typing import Dict

from projects.models import ProjectStudent, ReportingPeriod, \
    ReportingPeriodKey, Project


def get_project_reporting_periods(student, term) -> Dict[ProjectStudent, ReportingPeriod]:
    """
    Returns map of student project to reporting periods in selected term
    """
    reporting_periods = {}
    student_projects = set(ProjectStudent.objects
                           .exclude(project__status=Project.Statuses.CANCELED)
                           .filter(project__semester=term,
                                   student_id=student.pk)
                           .select_related('project', 'project__branch'))
    if student_projects:
        periods = ReportingPeriod.get_periods(term=term)
        for sp in student_projects:
            sp.project.semester = term
            key = ReportingPeriodKey(sp.project.branch.code,
                                     sp.project.project_type)
            if key in periods:
                reporting_periods[sp] = periods[key]
    return reporting_periods
