import logging
from datetime import timedelta
from enum import Enum, auto
from itertools import islice
from typing import Any, Iterable, List, Optional, Sequence, Union, cast

from django.contrib.sites.models import Site
from django.core.files.uploadedfile import UploadedFile
from django.db import router, transaction
from django.db.models import (
    Avg, Count, F, OuterRef, Q, QuerySet, Subquery, TextField, Value
)
from django.db.models.functions import Coalesce, Concat
from django.db.models.signals import post_save
from django.utils.timezone import now

from core.models import Branch
from core.services import SoftDeleteService
from core.timezone import now_local
from core.timezone.constants import DATE_FORMAT_RU
from courses.managers import CourseClassQuerySet
from courses.models import (
    Assignment, AssignmentAttachment, Course, CourseClass, CourseGroupModes,
    CourseTeacher, StudentGroupTypes
)
from learning.models import (
    AssignmentComment, AssignmentNotification, AssignmentSubmissionTypes,
    CourseNewsNotification, Enrollment, Event, StudentAssignment, StudentGroup,
    StudentGroupAssignee
)
from learning.settings import StudentStatuses
from users.constants import Roles
from users.models import StudentProfile, StudentTypes, User

logger = logging.getLogger(__name__)


class StudentProfileError(Exception):
    pass


# FIXME: get profile for Invited students from the current term ONLY
# FIXME: store term of registration or get date range for the term of registration
def get_student_profile(user: User, site, profile_type=None,
                        filters: Optional[List[Q]] = None) -> Optional[StudentProfile]:
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


def recreate_assignments_for_student(enrollment):
    """Resets progress for existing and creates missing assignments"""
    for a in enrollment.course.assignment_set.all():
        AssignmentService.recreate_student_assignment(a, enrollment)


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
    def add(course: Course, **attrs):
        if course.group_mode == CourseGroupModes.BRANCH:
            branch = attrs.pop('branch')
            group, _ = (StudentGroup.objects.get_or_create(
                course_id=course.pk,
                type=StudentGroupTypes.BRANCH,
                branch_id=branch.pk,
                defaults={
                    "name_ru": branch.name_ru,
                    "name_en": branch.name_en,
                    **attrs,
                }))
            return group
        elif course.group_mode == CourseGroupModes.MANUAL:
            group_name = attrs.pop('name', None)
            if not group_name:
                raise StudentGroupError('Provide a unique name for group')
            group, _ = (StudentGroup.objects.get_or_create(
                course_id=course.pk,
                type=StudentGroupTypes.MANUAL,
                name=group_name,
                defaults=attrs))
            return group
        else:
            raise StudentGroupError("Student group mode is not supported")

    @staticmethod
    def remove(course: Course, instance):
        if course.group_mode == CourseGroupModes.BRANCH:
            assert isinstance(instance, Branch)
            StudentGroup.objects.filter(course_id=course.pk,
                                        branch_id=instance.pk).delete()
        else:
            StudentGroup.objects.filter(course_id=course.pk,
                                        pk=instance.pk).delete()

    @staticmethod
    def resolve(course: Course, student: User, site: Union[Site, int],
                enrollment_key: Optional[str] = None):
        """
        Returns the target or associated student group for the course. Assumed
        that student is not enrolled in the course.
        """
        if course.group_mode == CourseGroupModes.BRANCH:
            student_profile = student.get_student_profile(site)
            if not student_profile:
                return
            student_group = (StudentGroup.objects
                             .filter(course=course,
                                     type=StudentGroupTypes.BRANCH,
                                     branch_id=student_profile.branch_id)
                             .first())
            # Student could be enrolled in the course through the admin
            # interface without meeting the branch requirements. In that case
            # add them to the special group
            if student_group is None:
                student_group, _ = StudentGroup.objects.get_or_create(
                    course=course,
                    type=StudentGroupTypes.SYSTEM,
                    branch_id__isnull=True,
                    defaults={"name_en": "Others", "name_ru": "Другие"})
            return student_group
        elif course.group_mode == CourseGroupModes.MANUAL:
            if enrollment_key:
                try:
                    return StudentGroup.objects.get(course=course,
                                                    type=StudentGroupTypes.MANUAL,
                                                    enrollment_key=enrollment_key)
                except StudentGroup.DoesNotExist:
                    raise GroupEnrollmentKeyError
            else:
                # Вытаскивать по факту из уже записанного?
                student_group, _ = StudentGroup.objects.get_or_create(
                    course=course,
                    type=StudentGroupTypes.SYSTEM,
                    branch_id__isnull=True,
                    defaults={
                        "name_en": "Without Group",
                        "name_ru": "Без группы"
                    })
                return student_group
        raise GroupEnrollmentKeyError

    @classmethod
    def get_choices(cls, course: Course):
        choices = []
        qs = StudentGroup.objects.filter(course=course).order_by('pk')
        groups = list(qs)
        sites_count = 1
        if course.group_mode == CourseGroupModes.BRANCH:
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

    @staticmethod
    def get_assignees(
        student_group,
        assignment: Optional[Assignment] = None) -> List[CourseTeacher]:
        default_and_overridden = Q(assignment__isnull=True)
        if assignment:
            default_and_overridden |= Q(assignment=assignment)
        assignees = list(StudentGroupAssignee.objects
                         .filter(default_and_overridden,
                                 student_group=student_group)
                         .select_related('assignee__teacher'))
        # Default values could be overwritten by assignment specific
        if any(ga.assignment_id is not None for ga in assignees):
            # Remove defaults
            assignees = [ga for ga in assignees if ga.assignment_id]
        filtered = [ga.assignee for ga in assignees]
        return filtered


class AssignmentService:
    @staticmethod
    def process_attachments(assignment: Assignment,
                            attachments: List[UploadedFile]):
        if attachments:
            for attachment in attachments:
                (AssignmentAttachment.objects
                 .create(assignment=assignment, attachment=attachment))

    @staticmethod
    def setup_assignees(assignment: Assignment):
        """
        Copy course homework reviewers to the assignment settings for further
        customization.
        """
        course_reviewers = assignment.course.course_teachers.filter(
            roles=CourseTeacher.roles.reviewer
        )
        assignment.assignees.add(*course_reviewers)

    @classmethod
    def recreate_student_assignment(cls, assignment: Assignment,
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
    def bulk_create_student_assignments(
        cls, assignment: Assignment,
        for_groups: Optional[Iterable[Optional[int]]] = None):
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
    def bulk_remove_student_assignments(
        assignment: Assignment,
        for_groups: Optional[Iterable[Optional[int]]] = None):
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

    @classmethod
    def get_mean_execution_time(cls, assignment: Assignment):
        stats = (StudentAssignment.objects
                 .filter(assignment=assignment)
                 .aggregate(mean=Avg('execution_time')))
        return stats['mean']

    @classmethod
    def get_median_execution_time(cls, assignment: Assignment) -> Optional[timedelta]:
        queryset = (StudentAssignment.objects
                    .filter(assignment=assignment)
                    .exclude(execution_time__isnull=True))
        count = queryset.count()
        if not count:
            return None
        values = (queryset
                  .values_list('execution_time', flat=True)
                  .order_by('execution_time'))
        if count % 2 == 1:
            return values[count // 2]
        else:
            mid = count // 2
            # TODO: Change the query so that null durations are filtered out.
            return sum(values[mid - 1:mid + 1], timedelta()) / 2  # type: ignore


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
            # At this moment enrollment instance not in a consistent state -
            # it has no student group, etc
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
                enrollment.refresh_from_db()
                # Send signal to trigger callbacks:
                # - update learners count
                post_save.send(Enrollment, instance=enrollment, created=created)
                recreate_assignments_for_student(enrollment)
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
            remove_course_notifications_for_student(enrollment)


def remove_course_notifications_for_student(enrollment: Enrollment):
    (AssignmentNotification.objects
     .filter(user_id=enrollment.student_id,
             student_assignment__assignment__course_id=enrollment.course_id)
     .delete())
    (CourseNewsNotification.objects
     .filter(user_id=enrollment.student_id,
             course_offering_news__course_id=enrollment.course_id)
     .delete())


def notify_student_new_assignment(student_assignment, commit=True):
    obj = AssignmentNotification(user_id=student_assignment.student_id,
                                 student_assignment_id=student_assignment.pk,
                                 is_about_creation=True)
    if commit:
        obj.save()
    return obj


# FIXME: для решений в Я.Контест неплохо бы отправлять уведомления учителям, только если это gerrit.bot?
def create_notifications_about_new_submission(submission: AssignmentComment):
    if not submission.pk:
        return
    notifications = []
    student_assignment: StudentAssignment = submission.student_assignment
    if submission.author_id != student_assignment.student_id:
        # Generate notification for student
        n = AssignmentNotification(user_id=student_assignment.student_id,
                                   student_assignment=student_assignment)
        notifications.append(n)
    else:
        assignees: List[Any] = []
        assignment = student_assignment.assignment
        if student_assignment.assignee_id:
            assignees.append(student_assignment.assignee.teacher_id)  # type: ignore[union-attr]
        else:
            # There is no teacher assigned, check student group assignees
            try:
                enrollment = (Enrollment.active
                              .get(course_id=assignment.course_id,
                                   student_id=student_assignment.student_id))
            except Enrollment.DoesNotExist:
                logger.info("No need to send assignment notifications "
                            "for student that left the course")
                return
            student_group = enrollment.student_group_id
            group_assignees = StudentGroupService.get_assignees(student_group,
                                                                assignment)
            if group_assignees:
                assignees = [a.teacher_id for a in group_assignees]
            else:
                assignees = [a.teacher_id for a in assignment.assignees.all()]
        # Skip course teachers who don't want receive notifications
        if assignees:
            course_teachers = (CourseTeacher.objects
                               .filter(course=assignment.course_id))
            notifications_enabled = {ct.teacher_id for ct in course_teachers
                                     if ct.notify_by_default}
            assignees = [a for a in assignees if a in notifications_enabled]
        is_solution = (submission.type == AssignmentSubmissionTypes.SOLUTION)
        for a in assignees:
            n = AssignmentNotification(user_id=a,
                                       student_assignment=student_assignment,
                                       is_about_passed=is_solution)
            notifications.append(n)
    AssignmentNotification.objects.bulk_create(notifications)
    return len(notifications)


def update_student_assignment_derivable_fields(comment):
    """
    Optimize db queries by reimplementing next logic:
        student_assignment.compute_fields('first_student_comment_at')
        student_assignment.compute_fields('last_comment_from')
    """
    if not comment.pk:
        return
    sa: StudentAssignment = comment.student_assignment
    fields = {"modified": now()}
    if comment.author_id == sa.student_id:
        # FIXME: includes solutions. is it ok?
        other_comments = (sa.assignmentcomment_set(manager='published')
                          .filter(author_id=comment.author_id)
                          .exclude(pk=comment.pk))
        is_first_comment = not other_comments.exists()
        if is_first_comment:
            fields["first_student_comment_at"] = comment.created
        fields["last_comment_from"] = sa.CommentAuthorTypes.STUDENT
    else:
        fields["last_comment_from"] = sa.CommentAuthorTypes.TEACHER
    StudentAssignment.objects.filter(pk=sa.pk).update(**fields)
    for attr_name, attr_value in fields.items():
        setattr(sa, attr_name, attr_value)


def trigger_auto_assign_for_student_assignment(submission: AssignmentComment):
    """
    Auto assign teacher in a lazy manner (on student activity) when
    student group has assignee.
    """
    student_assignment = submission.student_assignment
    # Trigger on student activity
    if submission.author_id != student_assignment.student_id:
        return
    if not student_assignment.trigger_auto_assign:
        return
    update_fields = ['trigger_auto_assign', 'modified']
    assignment = student_assignment.assignment
    try:
        enrollment = (Enrollment.active
                      .select_related('student_group')
                      .get(course_id=assignment.course_id,
                           student_id=student_assignment.student_id))
    except Enrollment.DoesNotExist:
        logger.error('Auto assign triggered for student that left the course')
        return
    student_group = enrollment.student_group
    assignees = StudentGroupService.get_assignees(student_group, assignment)
    if assignees:
        update_fields.append('assignee')
        if len(assignees) == 1:
            assignee = assignees[0]
        else:
            # TODO: set all of them as watchers instead or get random
            assignee = assignees[0]
        student_assignment.assignee = assignee
    student_assignment.trigger_auto_assign = False
    student_assignment.modified = now()
    student_assignment.save(update_fields=update_fields)


def get_student_classes(user, filters: Optional[List[Q]] = None,
                        with_venue=False) -> CourseClassQuerySet:
    # Student could be manually enrolled in the course without
    # checking branch compatibility, skip filtering by branch
    qs = (get_classes([], filters)
          .for_student(user)
          .order_by("-date", "-starts_at"))
    if with_venue:
        qs = qs.select_related('venue', 'venue__location')
    return qs


def get_teacher_classes(user, filters: Optional[List[Q]] = None,
                        with_venue=False) -> CourseClassQuerySet:
    qs = get_classes([], filters).for_teacher(user)
    if with_venue:
        qs = qs.select_related('venue', 'venue__location')
    return qs


def get_classes(branch_list, filters: Optional[List[Q]] = None) -> CourseClassQuerySet:
    filters = filters or []
    return (CourseClass.objects
            .filter(*filters)
            .in_branches(*branch_list)
            .select_calendar_data())


def get_study_events(filters: Optional[List[Q]] = None) -> QuerySet:
    filters = filters or []
    return (Event.objects
            .filter(*filters)
            .select_related('venue')
            .order_by('date', 'starts_at'))


def get_teacher_assignments(user):
    """
    Returns assignments where user is participating as a teacher.
    """
    return (Assignment.objects
            .filter(course__teachers=user,
                    course__course_teachers__roles=~CourseTeacher.roles.spectator)
            .select_related('course',
                            'course__meta_course',
                            'course__semester'))


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
    enrolled student. This roles do not overlap in the same course.
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
    # FIXME: separate into teacher_spectator and teacher_regular?
    if Roles.TEACHER in user.roles and user in course.teachers.all():
        # Teacher role has a higher precedence
        role = CourseRole.TEACHER
    return role
