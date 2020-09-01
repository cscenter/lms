from enum import Enum, auto
from itertools import islice
from typing import List, Iterable, Union, Optional

from django.contrib.sites.models import Site
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction, router
from django.db.models import Q, OuterRef, Value, F, TextField, QuerySet, \
    Subquery, Count
from django.db.models.functions import Concat, Coalesce
from django.utils.timezone import now

from core.models import Branch
from core.services import SoftDeleteService
from core.timezone import now_local
from core.timezone.constants import DATE_FORMAT_RU
from courses.managers import CourseClassQuerySet
from courses.models import Course, Assignment, AssignmentAttachment, \
    StudentGroupTypes, CourseClass, CourseTeacher
from learning.models import Enrollment, StudentAssignment, \
    AssignmentNotification, StudentGroup, Event
from learning.settings import StudentStatuses
from users.models import User, StudentProfile, StudentTypes


class StudentProfileError(Exception):
    pass


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
        if "year_of_curriculum" not in profile_fields:
            msg = "Year of curriculum is not set for the regular student"
            raise StudentProfileError(msg)
    # FIXME: Prevent creating 2 profiles for invited student in the same
    # term through admin interface
    new_student_profile = StudentProfile(**profile_fields)
    new_student_profile.save()
    return new_student_profile


def populate_assignments_for_student(enrollment):
    for a in enrollment.course.assignment_set.all():
        AssignmentService.create_student_assignment(a, enrollment)


def get_learners_count_subquery(outer_ref: OuterRef):
    from learning.models import Enrollment
    return Coalesce(Subquery(
        (Enrollment.active
         .filter(course_id=outer_ref)
         .order_by()
         .values('course')  # group by
         .annotate(total=Count("*"))
         .values("total"))
    ), Value(0))


def update_course_learners_count(course_id):
    Course.objects.filter(id=course_id).update(
        learners_count=get_learners_count_subquery(outer_ref=OuterRef('id'))
    )


def course_failed_by_student(course: Course, student, enrollment=None) -> bool:
    """Checks that student didn't fail the completed course"""
    from learning.models import Enrollment
    if course.is_club_course or not course.is_completed:
        return False
    bad_grades = (Enrollment.GRADES.UNSATISFACTORY,
                  Enrollment.GRADES.NOT_GRADED)
    if enrollment:
        return enrollment.grade in bad_grades
    return (Enrollment.active
            .filter(student_id=student.id,
                    course_id=course.id,
                    grade__in=bad_grades)
            .exists())


class StudentGroupError(Exception):
    pass


class GroupEnrollmentKeyError(StudentGroupError):
    pass


class StudentGroupService:
    @staticmethod
    def add(course: Course, branch: Branch):
        if course.group_mode == StudentGroupTypes.BRANCH:
            group, _ = (StudentGroup.objects.get_or_create(
                course_id=course.pk,
                type=StudentGroupTypes.BRANCH,
                branch_id=branch.pk,
                defaults={
                    "name_ru": branch.name_ru,
                    "name_en": branch.name_en,
                }))
        else:
            raise StudentGroupError("Only `branch` group mode is supported")

    @staticmethod
    def remove(course: Course, instance):
        if course.group_mode == StudentGroupTypes.BRANCH:
            assert isinstance(instance, Branch)
            StudentGroup.objects.filter(course_id=course.pk,
                                        branch_id=instance.pk).delete()
        else:
            StudentGroup.objects.filter(course_id=course.pk,
                                        pk=instance.pk).delete()

    @staticmethod
    def resolve(course: Course, student: User, site: Union[Site, int],
                enrollment_key: str = None):
        """
        Returns the target or associated student group for the course.
        """
        if course.group_mode == StudentGroupTypes.BRANCH:
            # It's possible to miss student group here since student could be
            # added to the course through the admin interface without
            # checking all the requirements
            student_profile = student.get_student_profile(site)
            if not student_profile:
                return
            return (StudentGroup.objects
                    .filter(course=course, branch_id=student_profile.branch_id)
                    .first())
        elif course.group_mode == StudentGroupTypes.MANUAL:
            try:
                return StudentGroup.objects.get(course=course,
                                                enrollment_key=enrollment_key)
            except StudentGroup.DoesNotExist:
                raise GroupEnrollmentKeyError
        elif course.group_mode == StudentGroupTypes.NO_GROUPS:
            return None

    @classmethod
    def get_choices(cls, course: Course):
        choices = []
        qs = StudentGroup.objects.filter(course=course).order_by('pk')
        groups = list(qs)
        sites_count = 1
        if course.group_mode == StudentGroupTypes.BRANCH:
            sites = set()
            for g in groups:
                # Special case when student group manually added in admin
                if g.branch_id:
                    g.branch = Branch.objects.get_by_pk(g.branch_id)
                    sites.add(g.branch.site_id)
            sites_count = len(sites)
        for g in groups:
            label = cls._get_choice_label(g, sites_count)
            choices.append((str(g.pk), label))
        return choices

    @staticmethod
    def _get_choice_label(student_group, sites_count):
        if student_group.type == StudentGroupTypes.BRANCH and sites_count > 1:
            return f"{student_group.name} [{student_group.branch.site}]"
        return student_group.name


class AssignmentService:
    @staticmethod
    def process_attachments(assignment: Assignment,
                            attachments: List[UploadedFile]):
        if attachments:
            for attachment in attachments:
                (AssignmentAttachment.objects
                 .create(assignment=assignment, attachment=attachment))

    @staticmethod
    def setup_notification_settings(assignment: Assignment):
        """
        Auto populate assignment notification settings based on
        default course notification settings.
        """
        course_teachers = assignment.course.course_teachers.all()
        notify_teachers = [t.pk for t in course_teachers if t.notify_by_default]
        assignment.notify_teachers.add(*notify_teachers)

    @classmethod
    def create_student_assignment(cls, assignment: Assignment,
                                  enrollment: Enrollment):
        """
        Creates or restores record for tracking student progress on assignment
        if the assignment is not restricted for the student's group.
        """
        restricted_to = list(sg.pk for sg in assignment.restricted_to.all())
        if restricted_to and enrollment.student_group_id not in restricted_to:
            return
        return StudentAssignment.base.update_or_create(
            assignment=assignment, student_id=enrollment.student_id,
            defaults={'deleted_at': None, 'score': None, 'execution_time': None})

    @classmethod
    def _restore_student_assignments(cls, assignment: Assignment,
                                     student_ids: Iterable[int]):
        qs = (StudentAssignment.trash
              .filter(assignment=assignment, student_id__in=student_ids))
        for student_assignment in qs:
            # TODO: reset score? execution_time?
            student_assignment.restore()

    # TODO: send notification to teachers except assignment publisher
    @classmethod
    def bulk_create_student_assignments(cls, assignment: Assignment,
                                        for_groups: Iterable[Union[int, None]] = None):
        """
        Generates individual assignments to store student progress.
        By default it creates record for each enrolled student who's not
        expelled or on academic leave and the assignment is not restricted
        for the group in which the student participates in the course.

        You can restrict processed enrollments to the specific groups by
        setting  `for_groups`.
        Special case `for_groups=[..., None]` - include enrollments without
        student group.
        """
        filters = [
            Q(course_id=assignment.course_id),
            ~Q(student_profile__status__in=StudentStatuses.inactive_statuses)
        ]
        restrict_to = list(sg.pk for sg in assignment.restricted_to.all())
        if for_groups is not None:
            has_null = None in for_groups
            if restrict_to:
                for_groups = [pk for pk in for_groups if pk in restrict_to]
            # Queryset should be empty if `for_groups` is an empty list
            groups_q = Q(student_group_id__in=for_groups)
            if has_null:
                groups_q |= Q(student_group__isnull=True)
            filters.append(groups_q)
        elif restrict_to:
            # Exclude enrollments without student group if assignment is
            # restricted to some groups
            filters.append(Q(student_group_id__in=restrict_to))
        pks = list(Enrollment.active
                   .filter(*filters)
                   .values_list("student_id", flat=True))
        # Create/update records in separate steps to avoid tons of save points
        in_trash = set(StudentAssignment.trash
                       .filter(assignment=assignment, student_id__in=pks)
                       .values_list('student_id', flat=True))
        if in_trash:
            cls._restore_student_assignments(assignment, in_trash)
        batch_size = 100
        to_create = (sid for sid in pks if sid not in in_trash)
        objs = (StudentAssignment(assignment=assignment, student_id=student_id)
                for student_id in to_create)
        while True:
            batch = list(islice(objs, batch_size))
            if not batch:
                break
            StudentAssignment.objects.bulk_create(batch, batch_size)
        # Generate notifications
        created = (StudentAssignment.objects
                   .filter(assignment=assignment, student_id__in=pks)
                   .values_list('pk', 'student_id', named=True))
        objs = (notify_student_new_assignment(sa, commit=False) for sa
                in created)
        batch_size = 100
        while True:
            batch = list(islice(objs, batch_size))
            if not batch:
                break
            AssignmentNotification.objects.bulk_create(batch, batch_size)

    @staticmethod
    def bulk_remove_student_assignments(assignment: Assignment,
                                        for_groups: Iterable[Union[int, None]] = None):
        filters = [Q(assignment=assignment)]
        if for_groups is not None:
            filters_ = [Q(course_id=assignment.course_id)]
            groups_q = Q(student_group_id__in=for_groups)
            has_null = None in for_groups
            if has_null:
                groups_q |= Q(student_group__isnull=True)
            filters_.append(groups_q)
            students = (Enrollment.objects
                        .filter(*filters_)
                        .values_list('student_id', flat=True))
            filters.append(Q(student__in=students))
        to_delete = list(StudentAssignment.objects.filter(*filters))
        using = router.db_for_write(StudentAssignment)
        SoftDeleteService(using).delete(to_delete)
        # Hard delete notifications
        (AssignmentNotification.objects
         .filter(student_assignment__in=to_delete)
         .delete())

    @classmethod
    def sync_student_assignments(cls, assignment: Assignment):
        """
        Sync student assignments with assignment restriction requirements
        by deleting or creating missing records.
        """
        ss = (StudentAssignment.objects
              .filter(assignment=assignment)
              .values_list('student_id', flat=True))
        existing_groups = set(Enrollment.objects
                              .filter(course_id=assignment.course_id,
                                      student__in=ss)
                              .values_list('student_group_id', flat=True)
                              .distinct())
        restricted_to_groups = set(sg.pk for sg in assignment.restricted_to.all())
        if not restricted_to_groups:
            restricted_to_groups = set(StudentGroup.objects
                                       .filter(course_id=assignment.course_id)
                                       .values_list('pk', flat=True))
            # Special case - students without student group
            restricted_to_groups.add(None)
        groups_add = restricted_to_groups.difference(existing_groups)
        if groups_add:
            cls.bulk_create_student_assignments(assignment,
                                                for_groups=groups_add)
        groups_remove = existing_groups.difference(restricted_to_groups)
        if groups_remove:
            cls.bulk_remove_student_assignments(assignment,
                                                for_groups=groups_remove)


class EnrollmentError(Exception):
    pass


class AlreadyEnrolled(EnrollmentError):
    pass


class CourseCapacityFull(EnrollmentError):
    pass


class EnrollmentService:
    @staticmethod
    def _format_reason_record(reason_text: str, course: Course):
        """Append date to the enter/leave reason text"""
        timezone = course.get_timezone()
        today = now_local(timezone).strftime(DATE_FORMAT_RU)
        return f'{today}\n{reason_text}\n\n'

    @classmethod
    def enroll(cls, student: StudentProfile, course: Course,
               reason_entry='', **attrs):
        if reason_entry:
            new_record = cls._format_reason_record(reason_entry, course)
            reason_entry = Concat(Value(new_record),
                                  F('reason_entry'),
                                  output_field=TextField())
        with transaction.atomic():
            enrollment, created = (Enrollment.objects.get_or_create(
                student=student.user, course=course,
                defaults={'is_deleted': True, 'student_profile': student}))
            if not enrollment.is_deleted:
                raise AlreadyEnrolled
            # Use sharable lock for concurrent enrollments if necessary to
            # control participants number. A blocking operation since `nowait`
            # is not used.
            if course.is_capacity_limited:
                locked = Course.objects.select_for_update().get(pk=course.pk)
            # Try to update enrollment to the `active` state
            filters = [Q(pk=enrollment.pk), Q(is_deleted=True)]
            if course.is_capacity_limited:
                learners_count = get_learners_count_subquery(
                    outer_ref=OuterRef('course_id')
                )
                filters.append(Q(course__capacity__gt=learners_count))
            attrs.update({
                "is_deleted": False,
                "student_profile": student,
                "reason_entry": reason_entry
            })
            updated = (Enrollment.objects
                       .filter(*filters)
                       .update(**attrs))
            if not updated:
                # At this point we don't know the exact reason why row wasn't
                # updated. It could happen if the enrollment state was
                # `is_deleted=False` or no places left or both.
                # The first one is quit impossible (user should do concurrent
                # requests) and still should be considered as success, so
                # let's take into account only the second case.
                if course.is_capacity_limited:
                    raise CourseCapacityFull
            else:
                if not created:
                    populate_assignments_for_student(enrollment)
                update_course_learners_count(course.pk)
        enrollment.refresh_from_db()
        return enrollment

    @classmethod
    def leave(cls, enrollment: Enrollment, reason_leave=''):
        update_fields = ['is_deleted']
        enrollment.is_deleted = True
        if reason_leave:
            new_record = cls._format_reason_record(reason_leave,
                                                   enrollment.course)
            enrollment.reason_leave = Concat(
                Value(new_record),
                F('reason_leave'),
                output_field=TextField())
            update_fields.append('reason_leave')
        with transaction.atomic():
            enrollment.save(update_fields=update_fields)


def notify_student_new_assignment(student_assignment, commit=True):
    obj = AssignmentNotification(user_id=student_assignment.student_id,
                                 student_assignment_id=student_assignment.pk,
                                 is_about_creation=True)
    if commit:
        obj.save()
    return obj


def notify_new_assignment_comment(comment):
    """
    Notify teachers if student leave a comment, otherwise notify student.
    Update `first_student_comment_at` and `last_comment_from`
    StudentAssignment model fields.
    """
    sa: StudentAssignment = comment.student_assignment
    notifications = []
    sa_update_dict = {"modified": now()}
    if comment.author_id == sa.student_id:
        other_comments = (sa.assignmentcomment_set(manager='published')
                          .filter(author_id=comment.author_id)
                          .exclude(pk=comment.pk))
        is_first_comment = not other_comments.exists()
        is_about_passed = sa.assignment.is_online and is_first_comment

        teachers = comment.student_assignment.assignment.notify_teachers.all()
        for t in teachers:
            notifications.append(
                AssignmentNotification(user_id=t.teacher_id,
                                       student_assignment=sa,
                                       is_about_passed=is_about_passed))

        if is_first_comment:
            sa_update_dict["first_student_comment_at"] = comment.created
        sa_update_dict["last_comment_from"] = sa.CommentAuthorTypes.STUDENT
    else:
        sa_update_dict["last_comment_from"] = sa.CommentAuthorTypes.TEACHER
        notifications.append(
            AssignmentNotification(user_id=sa.student_id, student_assignment=sa)
        )
    AssignmentNotification.objects.bulk_create(notifications)
    StudentAssignment.objects.filter(pk=sa.pk).update(**sa_update_dict)
    for attr_name, attr_value in sa_update_dict.items():
        setattr(sa, attr_name, attr_value)


def get_student_classes(user, filters: List[Q] = None,
                        with_venue=False) -> CourseClassQuerySet:
    # Student could be manually enrolled in the course without
    # checking branch compatibility, skip filtering by branch
    branch_list = []
    qs = (get_classes(branch_list, filters)
          .for_student(user)
          .order_by("-date", "-starts_at"))
    if with_venue:
        qs = qs.select_related('venue', 'venue__location')
    return qs


def get_teacher_classes(user, filters: List[Q] = None,
                        with_venue=False) -> CourseClassQuerySet:
    branch_list = []
    qs = get_classes(branch_list, filters).for_teacher(user)
    if with_venue:
        qs = qs.select_related('venue', 'venue__location')
    return qs


def get_classes(branch_list, filters: List[Q] = None) -> CourseClassQuerySet:
    filters = filters or []
    return (CourseClass.objects
            .filter(*filters)
            .in_branches(*branch_list)
            .select_calendar_data())


def get_study_events(filters: List[Q] = None) -> QuerySet:
    filters = filters or []
    return (Event.objects
            .filter(*filters)
            .select_related('venue')
            .order_by('date', 'starts_at'))


class CourseRole(Enum):
    NO_ROLE = auto()
    STUDENT_REGULAR = auto()  # Enrolled active student
    # Restrict access to the course for enrolled students in next cases:
    #   * student failed the course
    #   * student was expelled or in academic leave
    STUDENT_RESTRICT = auto()
    TEACHER = auto()  # Any teacher from the same meta course
    CURATOR = auto()


def course_access_role(*, course, user) -> CourseRole:
    """
    Some course data (e.g. assignments, news) are private and accessible
    depending on the user role: curator, course teacher or
    enrolled student. This UserRoles do not overlap in the same course.
    """
    if not user.is_authenticated:
        return CourseRole.NO_ROLE
    if user.is_curator:
        return CourseRole.CURATOR
    role = CourseRole.NO_ROLE
    enrollment = user.get_enrollment(course.pk)
    if enrollment:
        failed = course_failed_by_student(course, user, enrollment)
        student_status = enrollment.student_profile.status
        if not failed and not StudentStatuses.is_inactive(student_status):
            role = CourseRole.STUDENT_REGULAR
        else:
            role = CourseRole.STUDENT_RESTRICT
    # Teachers from the same course permits to view the news/assignments/etc
    all_meta_course_teachers = (CourseTeacher.objects
                           .for_meta_course(course.meta_course)
                           .values_list('teacher_id', flat=True))
    if user.is_teacher and user.pk in all_meta_course_teachers:
        # Overrides student role if a teacher enrolled in his own course
        role = CourseRole.TEACHER
    return role
