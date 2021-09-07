import datetime
from collections import defaultdict
from enum import Enum, auto
from typing import Any, Dict, List, Literal, Optional

from registration.models import RegistrationProfile

from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils.timezone import now

from auth.registry import role_registry
from core.models import Branch
from core.timezone import get_now_utc
from core.timezone.typing import Timezone
from courses.models import Semester
from learning.models import GraduateProfile
from learning.settings import StudentStatuses
from users.constants import GenderTypes, Roles
from users.models import (
    OnlineCourseRecord, StudentProfile, StudentStatusLog, StudentTypes, User, UserGroup
)

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
                        .select_related('user')
                        .prefetch_related('academic_disciplines'))
    is_update_student_status = now().date() >= graduated_on
    if is_update_student_status and not created_by:
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
            if created:
                # Copy academic disciplines from the student profile
                model_class = GraduateProfile.academic_disciplines.through
                disciplines = []
                for discipline in student_profile.academic_disciplines.all():
                    d = model_class(academicdiscipline_id=discipline.pk,
                                    graduateprofile_id=graduate.pk)
                    disciplines.append(d)
                model_class.objects.bulk_create(disciplines)
            if is_update_student_status:
                update_student_status(student_profile, new_status=StudentStatuses.GRADUATE,
                                      editor=created_by, status_changed_at=graduated_on)
                # FIXME: replace student permission with graduate if there is no other active student profiles
                student_profile.user.remove_group(Roles.STUDENT)
                student_profile.user.add_group(Roles.GRADUATE)
    cache_key_pattern = GraduateProfile.HISTORY_CACHE_KEY_PATTERN
    cache_key = cache_key_pattern.format(site_id=site.pk)
    cache.delete(cache_key)


def get_graduate_profile(student_profile: StudentProfile) -> Optional[GraduateProfile]:
    return (GraduateProfile.active
            .filter(student_profile=student_profile)
            .prefetch_related('academic_disciplines')
            .first())


class StudentProfileError(Exception):
    pass


def create_student_profile(*, user: User, branch: Branch, profile_type,
                           year_of_admission, **fields) -> StudentProfile:
    profile_fields = {
        **fields,
        "user": user,
        "branch": branch,
        "type": profile_type,
        "year_of_admission": year_of_admission,
    }
    if profile_type == StudentTypes.REGULAR:
        # TODO: move to the .clean method
        if "year_of_curriculum" not in profile_fields:
            msg = "Year of curriculum is not set for the regular student"
            raise StudentProfileError(msg)
    # FIXME: Prevent creating 2 profiles for invited student in the same
    #  term through the admin interface
    student_profile = StudentProfile(**profile_fields)
    student_profile.full_clean()
    student_profile.save()
    # Append role permissions to the account if needed
    permission_role = StudentTypes.to_permission_role(student_profile.type)
    assign_role(account=student_profile.user, role=permission_role,
                site=student_profile.site)
    return student_profile


# FIXME: get profile for Invited students from the current term ONLY
# FIXME: store term of registration or get date range for the term of registration
def get_student_profile(user: User, site, profile_type=None,
                        filters: List[Q] = None) -> Optional[StudentProfile]:
    """
    Returns the most actual student profile on site for user.

    User could have multiple student profiles in different cases, e.g.:
    * They passed distance branch in 2011 and then applied to the
        offline branch in 2013
    * Student didn't meet the requirements and was expelled in the first
        semester but reapplied on general terms for the second time
    * Regular student "came back" as invited
    """
    filters = filters or []
    if profile_type is not None:
        filters.append(Q(type=profile_type))
    student_profile = (StudentProfile.objects
                       .filter(*filters, user=user, site=site)
                       .select_related('branch')
                       .order_by('-year_of_admission', '-priority', '-pk')
                       .first())
    if student_profile is not None:
        # It helps to invalidate cache on user model if profile were changed
        student_profile.user = user
    return student_profile


# TODO: try to make it an implementation detail of the `student_profile_update` service method
def update_student_status(student_profile: StudentProfile, *,
                          new_status: str, editor: User,
                          status_changed_at: Optional[datetime.date] = None) -> StudentProfile:
    is_studying_status = ''
    if new_status not in StudentStatuses.values and new_status != is_studying_status:
        raise ValidationError("Unknown Student Status", code="invalid")
    if student_profile.type == StudentTypes.INVITED:
        forbidden_statuses = {StudentStatuses.GRADUATE, StudentStatuses.WILL_GRADUATE}
        if new_status in forbidden_statuses:
            raise ValidationError(f"Status {new_status} is forbidden for invited students", code="forbidden")

    old_status = student_profile.tracker.previous('status')
    student_profile.status = new_status
    student_profile.save(update_fields=['status'])

    assign_or_revoke_student_role(student_profile=student_profile,
                                  old_status=old_status, new_status=new_status)

    log_entry = StudentStatusLog(status=new_status,
                                 student_profile=student_profile,
                                 entry_author=editor)

    if status_changed_at:
        log_entry.status_changed_at = status_changed_at

    log_entry.save()

    return student_profile


def assign_or_revoke_student_role(*, student_profile: StudentProfile,
                                  old_status: str, new_status: str) -> None:
    """
    Auto assign or remove permissions based on student status transition.

    Assumes that *new_status* already saved in DB.
    """
    transition = StudentStatusTransition.resolve(old_status, new_status)
    if transition == StudentStatusTransition.NEUTRAL:
        return None
    role = StudentTypes.to_permission_role(student_profile.type)
    user = student_profile.user
    site = student_profile.site
    if transition == StudentStatusTransition.DEACTIVATION:
        maybe_unassign_student_role(role, account=user, site=site)
        if old_status == StudentStatuses.GRADUATE:
            maybe_unassign_student_role(Roles.GRADUATE, account=user, site=site)
    elif transition == StudentStatusTransition.ACTIVATION:
        assign_role(account=user, role=role, site=site)
        if old_status == StudentStatuses.GRADUATE:
            maybe_unassign_student_role(Roles.GRADUATE, account=user, site=site)
    elif transition == StudentStatusTransition.GRADUATION:
        maybe_unassign_student_role(role, account=user, site=site)
        assign_role(account=user, role=Roles.GRADUATE, site=site)


def maybe_unassign_student_role(role: str, *, account: User, site: Site):
    """
    Removes permissions associated with a student *role* from the user account
    if all student profiles related to the same role are inactive or
    in a complete state (like GRADUATED)
    """
    if role not in role_registry:
        raise ValidationError(f"Role {role} is not registered")
    valid_roles = {Roles.STUDENT, Roles.GRADUATE, Roles.VOLUNTEER, Roles.INVITED, Roles.PARTNER}
    if role not in valid_roles:
        raise ValidationError(f"Role {role} is not a student role")
    profile_type = StudentTypes.from_permission_role(role)
    student_profiles = (StudentProfile.objects
                        .filter(user=account, type=profile_type, site=site)
                        .exclude(status=StudentStatuses.GRADUATE)
                        .only('status'))
    # TODO: has_active_student_profile?
    if all(not sp.is_active for sp in student_profiles):
        unassign_role(account=account, role=role, site=site)


class StudentStatusTransition(Enum):
    NEUTRAL = auto()  # active -> active, inactive -> inactive
    ACTIVATION = auto()
    DEACTIVATION = auto()
    GRADUATION = auto()  # any -> graduated

    @classmethod
    def resolve(cls, old_status: str, new_status: str) -> "StudentStatusTransition":
        """Returns transition type based on student old/new status values."""
        # We use `not inactive` here to cover implicit `studying` status
        was_active = old_status not in StudentStatuses.inactive_statuses
        is_active_now = new_status not in StudentStatuses.inactive_statuses
        if old_status == new_status:
            return StudentStatusTransition.NEUTRAL
        elif old_status == StudentStatuses.GRADUATE and is_active_now:
            return StudentStatusTransition.ACTIVATION
        elif old_status == StudentStatuses.GRADUATE and not is_active_now:
            return StudentStatusTransition.DEACTIVATION
        elif new_status == StudentStatuses.GRADUATE:
            return StudentStatusTransition.GRADUATION
        elif was_active and not is_active_now:
            return StudentStatusTransition.DEACTIVATION
        elif not was_active and is_active_now:
            return StudentStatusTransition.ACTIVATION
        else:
            return StudentStatusTransition.NEUTRAL


def create_account(*, username: str, password: str, email: str,
                   gender: str, time_zone: Timezone,
                   is_active: bool, **fields: Any) -> User:
    if gender not in GenderTypes.values:
        raise ValidationError("Unknown gender value", code="invalid")
    new_user = User(username=username,
                    email=email, gender=gender, time_zone=time_zone,
                    is_active=is_active, date_joined=get_now_utc(),
                    is_staff=False, is_superuser=False)
    new_user.set_password(password)
    valid_fields = {'first_name', 'last_name', 'patronymic', 'branch'}
    for field_name, field_value in fields.items():
        if field_name in valid_fields:
            setattr(new_user, field_name, field_value)

    new_user.full_clean()
    new_user.save()

    return new_user


def create_registration_profile(*, user: User,
                                activation_key: Optional[str] = None) -> RegistrationProfile:
    if user.is_active:
        raise ValidationError("Account is already activated", code="invalid")
    registration_profile = RegistrationProfile(user=user, activated=False)
    if activation_key is None:
        registration_profile.create_new_activation_key(save=False)
    registration_profile.full_clean()
    registration_profile.save()
    return registration_profile


class UniqueUsernameError(Exception):
    pass


def generate_username_from_email(email: str, attempts: int = 10):
    """Returns username generated from email or random if it's already exists."""
    username = email.split("@", maxsplit=1)[0]
    if User.objects.filter(username=username).exists():
        username = User.generate_random_username(attempts=attempts)
    if not username:
        raise UniqueUsernameError(f"Имя '{username}' уже занято. Случайное имя сгенерировать не удалось")
    return username


def assign_role(*, account: User, role: str, site: Site):
    if role not in Roles.values:
        raise ValidationError(f"Role {role} is not registered", code="invalid")
    UserGroup.objects.get_or_create(user=account, site=site, role=role)


def unassign_role(*, account: User, role: str, site: Site):
    if role not in Roles.values:
        raise ValidationError(f"Role {role} is not registered", code="invalid")
    UserGroup.objects.filter(user=account, site=site, role=role).delete()
