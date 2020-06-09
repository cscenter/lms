from typing import NamedTuple

from django.db.models import Count

from core.templatetags.core_tags import tex
from learning.settings import GradeTypes
from projects.constants import ProjectTypes


class DiplomaCourse(NamedTuple):
    type: str
    name: str
    teachers: str
    final_grade: str
    class_count: int = 0
    term: str = ''


def is_active_project(ps):
    return (not ps.project.is_external and
            not ps.project.is_canceled and
            ps.final_grade != GradeTypes.NOT_GRADED and
            ps.final_grade != GradeTypes.UNSATISFACTORY)


def generate_student_profiles_for_tex_diplomas(report):
    student_profiles = report.get_queryset()
    students = (sp.user for sp in student_profiles)
    courses_qs = (report.get_courses_queryset(students)
                  .annotate(classes_total=Count('courseclass')))
    courses = {c.pk: c for c in courses_qs}

    for student_profile in student_profiles:
        student = student_profile.user
        student.projects_progress = list(filter(is_active_project,
                                                student.projects_progress))
        student_courses = []
        enrollments = {}
        # Store the last passed course
        for e in student.enrollments_progress:
            meta_course_id = e.course.meta_course_id
            enrollments[meta_course_id] = e
        for e in enrollments.values():
            course = courses[e.course_id]
            teachers = ", ".join(ct.teacher.get_abbreviated_name(delimiter="~")
                                 for ct in course.course_teachers.all())
            diploma_course = DiplomaCourse(
                type="course",
                name=tex(course.meta_course.name),
                teachers=teachers,
                final_grade=str(e.grade_honest).lower(),
                class_count=course.classes_total * 2
            )
            student_courses.append(diploma_course)
        for c in student.shads:
            diploma_course = DiplomaCourse(
                type="shad",
                name=tex(c.name),
                teachers=c.teachers,
                final_grade=str(c.grade_display).lower(),
            )
            student_courses.append(diploma_course)
        student_courses.sort(key=lambda c: c.name)
        student.courses = student_courses
        delattr(student, "enrollments_progress")
        delattr(student, "shads")

        projects = []
        for ps in student.projects_progress:
            project = ps.project
            if project.project_type == ProjectTypes.research:
                project_type = 'theory'
            else:
                project_type = project.project_type
            diploma_course = DiplomaCourse(
                type=project_type,
                name=tex(project.name),
                teachers=", ".join(t.get_abbreviated_name(delimiter="~")
                                   for t in project.supervisors.all()),
                final_grade=str(ps.get_final_grade_display()).lower(),
                term=str(project.semester)
            )
            projects.append(diploma_course)
        student.projects = projects

    return student_profiles
