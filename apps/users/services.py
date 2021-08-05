import datetime
from collections import defaultdict
from typing import Any, Dict, List, Optional

from django.contrib.sites.models import Site
from django.core.cache import cache
from django.db import transaction
from django.utils.timezone import now

from courses.models import Semester
from learning.models import GraduateProfile
from learning.settings import StudentStatuses
from users.constants import Roles
from users.models import OnlineCourseRecord, StudentProfile, StudentStatusLog, User

AccountId = int


def get_student_progress(queryset,
                         exclude_grades: Optional[List[str]] = None,
                         until_term: Optional[Semester] = None) -> Dict[AccountId, Any]:
    """
    Prefetch student progress: courses, shad/online courses and projects

    Parameters:
        queryset:
        exclude_grades: Filter out records with provided grade values
        until_term: Get records before this term (inclusive)
    """

    from learning.models import Enrollment
    from projects.models import ProjectStudent

    from .models import SHADCourseRecord

    users = set(queryset.values_list('user_id', flat=True))
    progress: Dict[AccountId, Dict] = defaultdict(dict)
    enrollment_qs = (Enrollment.active
                     .filter(student_id__in=users)
                     .select_related('course',
                                     'course__meta_course',
                                     'course__semester',
                                     'course__main_branch')
                     .prefetch_related('course__course_teachers')
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


def get_student_status_history(student_profile: StudentProfile) -> List[StudentStatusLog]:
    return (StudentStatusLog.objects
            .filter(student_profile=student_profile)
            .order_by('-status_changed_at', '-pk'))


def create_graduate_profiles(site: Site, graduated_on: datetime.date,
                             created_by: Optional[User] = None) -> None:
    """
    Generate graduate profile for students with `will graduate` status. Update
    student profile status to `graduate` if graduation date already passed.
    """
    student_profiles = (StudentProfile.objects
                        .filter(status=StudentStatuses.WILL_GRADUATE,
                                branch__site=site)
                        .prefetch_related('academic_disciplines'))
    update_student_status = now().date() >= graduated_on
    if update_student_status and not created_by:
        created_by = User.objects.has_role(Roles.CURATOR).order_by('pk').first()
    for student_profile in student_profiles:
        with transaction.atomic():
            try:
                graduate = (GraduateProfile.objects
                            .select_for_update()
                            .get(student_profile=student_profile))
                created = False
            except GraduateProfile.DoesNotExist:
                graduate = GraduateProfile(student_profile=student_profile,
                                           details={})
                created = True
            graduate.graduated_on = graduated_on
            graduate.is_active = True
            graduate.save()
            if not created:
                graduate.academic_disciplines.clear()
            # Bulk copy academic disciplines without creating new transactions
            model_class = GraduateProfile.academic_disciplines.through
            disciplines = []
            for discipline in student_profile.academic_disciplines.all():
                d = model_class(academicdiscipline_id=discipline.pk,
                                graduateprofile_id=graduate.pk)
                disciplines.append(d)
            model_class.objects.bulk_create(disciplines)
            if update_student_status:
                (StudentProfile.objects
                 .filter(pk=student_profile.pk)
                 .update(status=StudentStatuses.GRADUATE))
                log_entry = StudentStatusLog(status=StudentStatuses.GRADUATE,
                                             student_profile=student_profile,
                                             entry_author=created_by)
                log_entry.save()
    cache_key_pattern = GraduateProfile.HISTORY_CACHE_KEY_PATTERN
    cache_key = cache_key_pattern.format(site_id=site.pk)
    cache.delete(cache_key)


def get_graduate_profile(student_profile: StudentProfile) -> Optional[GraduateProfile]:
    return (GraduateProfile.active
            .filter(student_profile=student_profile)
            .prefetch_related('academic_disciplines')
            .first())
