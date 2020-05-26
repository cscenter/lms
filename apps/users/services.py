import datetime
from collections import defaultdict
from typing import List, Dict

from django.contrib.sites.models import Site
from django.db import transaction

from learning.models import GraduateProfile
from learning.settings import GradeTypes, StudentStatuses
from users.models import OnlineCourseRecord, StudentProfile, User

AccountId = int


def get_student_progress(queryset,
                         exclude_grades: List[str] = None,
                         until_term: "Semester" = None):
    """
    Prefetch student progress: courses, shad/online courses and projects

    Parameters:
        queryset:
        exclude_grades: Filter out records with provided grade values
        until_term: Get records before this term (inclusive)
    """

    from .models import SHADCourseRecord
    from learning.models import Enrollment
    from projects.models import ProjectStudent

    users = set(queryset.values_list('user_id', flat=True))
    progress: Dict[AccountId, Dict] = defaultdict(dict)
    enrollment_qs = (Enrollment.active
                     .filter(student_id__in=users)
                     .select_related('course',
                                     'course__meta_course',
                                     'course__semester',
                                     'course__main_branch')
                     .prefetch_related('course__course_teachers')
                     .annotate(grade_weight=GradeTypes.to_int_case_expr())
                     .only('pk', 'created', 'student_id', 'course_id',
                           'grade'))
    if until_term:
        enrollment_qs = enrollment_qs.filter(
            course__semester__index__lte=until_term.index)
    if exclude_grades:
        enrollment_qs = enrollment_qs.exclude(grade__in=exclude_grades)
    for e in enrollment_qs:
        if 'enrollments' not in progress[e.student_id]:
            progress[e.student_id]['enrollments'] = []
        progress[e.student_id]['enrollments'].append(e)

    projects_queryset = (ProjectStudent.objects
                         .filter(student_id__in=users)
                         .select_related('project', 'project__semester')
                         .only('pk', 'project_id', 'student_id',
                               'final_grade', 'project__project_type',
                               'project__name', 'project__is_external',
                               'project__status',
                               'project__semester_id',
                               'project__semester__index',
                               'project__semester__year',
                               'project__semester__type', )
                         .order_by('project__semester__index',
                                   'project__name')
                         .prefetch_related("project__supervisors"))
    for obj in projects_queryset:
        if 'projects' not in progress[obj.student_id]:
            progress[obj.student_id]['projects'] = []
        progress[obj.student_id]['projects'].append(obj)

    shad_qs = SHADCourseRecord.objects.filter(student_id__in=users)
    if exclude_grades:
        shad_qs = shad_qs.exclude(grade__in=exclude_grades)
    if until_term:
        shad_qs = shad_qs.filter(semester__index__lte=until_term.index)
    for obj in shad_qs:
        if 'shad' not in progress[obj.student_id]:
            progress[obj.student_id]['shad'] = []
        progress[obj.student_id]['shad'].append(obj)

    online_courses_qs = OnlineCourseRecord.objects.filter(student_id__in=users)
    for obj in online_courses_qs:
        if 'online' not in progress[obj.student_id]:
            progress[obj.student_id]['online'] = []
        progress[obj.student_id]['online'].append(obj)

    return progress


def create_graduate_profiles(site: Site, graduated_on: datetime.date):
    """
    Create graduate profiles in draft state for all students with
    `will graduate` status.
    """
    student_profiles = (StudentProfile.objects
                        .filter(status=StudentStatuses.WILL_GRADUATE,
                                branch__site=site))
    for student_profile in student_profiles:
        with transaction.atomic():
            defaults = {
                "graduated_on": graduated_on,
                "details": {},
                "is_active": False
            }
            profile, created = GraduateProfile.objects.get_or_create(
                student_profile=student_profile,
                student=student_profile.user,  # FIXME: remove
                defaults=defaults)
            if not created:
                profile.save()


def get_graduate_profile(student_profile: StudentProfile):
    return (GraduateProfile.active
            .filter(student_profile=student_profile)
            .prefetch_related('academic_disciplines')
            .first())
