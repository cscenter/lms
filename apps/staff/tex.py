from datetime import date
from typing import NamedTuple, List

from core.templatetags.core_tags import tex
from learning.settings import GradeTypes
from projects.constants import ProjectTypes, ProjectGradeTypes
from study_programs.models import AcademicDiscipline


class DiplomaEntry(NamedTuple):
    type: str
    name: str
    teachers: str
    final_grade: str
    class_count: int = 0
    term: str = ''


class DiplomaStudent(NamedTuple):
    pk: int
    first_name: str
    patronymic: str
    last_name: str
    gender: str
    academic_disciplines: List[AcademicDiscipline]
    year_of_admission: int
    courses: List[DiplomaEntry]
    projects: List[DiplomaEntry]
    diploma_registration_number: str
    diploma_number: str
    diploma_issued_on: date


def is_active_project(ps):
    """
    Only internal projects that were finished (not cancelled) with a satisfactory grade should be shown
    in the usual or official diplomas. Note: on the contrary, in corresponding CSV files all projects are shown.
    """
    return (not ps.project.is_external and
            not ps.project.is_canceled and
            ps.final_grade != ProjectGradeTypes.NOT_GRADED and
            ps.final_grade != ProjectGradeTypes.UNSATISFACTORY)


def generate_tex_student_profile_for_diplomas(student_profile, courses, is_official=False):
    """
    Generates data class for a specified StudentProfile.
    Only fields that are necessary for the template of diplomas in TeX are included.
    Set `is_official=True` to include fields that are necessary for official diplomas.
    """
    student = student_profile.user
    student.projects_progress = list(filter(is_active_project,
                                            student.projects_progress))
    student_courses = []
    enrollments = {}
    # Store the last passed course
    for e in student.enrollments_progress:
        # Ignore club courses for official diplomas
        if is_official and e.course.is_club_course:
            continue
        meta_course_id = e.course.meta_course_id
        enrollments[meta_course_id] = e
    for e in enrollments.values():
        course = courses[e.course_id]
        teachers = ", ".join(ct.teacher.get_abbreviated_name(delimiter="~")
                             for ct in course.course_teachers.all())
        diploma_course = DiplomaEntry(
            type="course",
            name=tex(course.meta_course.name),
            teachers=teachers,
            final_grade=str(e.grade_honest).lower(),
            class_count=course.classes_total * 2
        )
        student_courses.append(diploma_course)
    for c in student.shads:
        diploma_course = DiplomaEntry(
            type="shad",
            name=tex(c.name),
            teachers=c.teachers,
            final_grade=str(c.grade_display).lower(),
        )
        student_courses.append(diploma_course)
    student_courses.sort(key=lambda c: c.name)

    projects = []
    for ps in student.projects_progress:
        project = ps.project
        if project.project_type == ProjectTypes.research:
            project_type = 'theory'
        else:
            project_type = project.project_type
        diploma_course = DiplomaEntry(
            type=project_type,
            name=tex(project.name),
            teachers=", ".join(t.get_abbreviated_name(delimiter="~")
                               for t in project.supervisors.all()),
            final_grade=str(ps.get_final_grade_display()).lower(),
            term=str(project.semester)
        )
        projects.append(diploma_course)

    data = {
        'pk': student.pk,
        'first_name': student.first_name,
        'patronymic': student.patronymic,
        'last_name': student.last_name,
        'gender': student.gender,
        'academic_disciplines': list(student_profile.academic_disciplines.all()),
        'year_of_admission': student_profile.year_of_admission,
        'courses': student_courses,
        'projects': projects,
        'diploma_registration_number': None,
        'diploma_number': None,
        'diploma_issued_on': None
    }

    if is_official:
        graduate_profile = student_profile.graduate_profile
        data.update({
            'diploma_registration_number': graduate_profile.diploma_registration_number,
            'diploma_number': graduate_profile.diploma_number,
            'diploma_issued_on': graduate_profile.diploma_issued_on
        })

    return DiplomaStudent(**data)
