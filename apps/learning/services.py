from typing import List, Iterable, Union

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction, router
from django.db.models import Q, OuterRef, Value, F, TextField
from django.db.models.functions import Concat
from django.utils.timezone import now

from core.db.expressions import SubqueryCount
from core.models import Branch
from core.services import SoftDeleteService
from core.timezone import now_local
from core.timezone.constants import DATE_FORMAT_RU
from courses.models import Course, Assignment, AssignmentAttachment, \
    StudentGroupTypes
from learning.models import Enrollment, StudentAssignment, \
    AssignmentNotification, StudentGroup
from learning.settings import StudentStatuses
from users.models import User


# FIXME: move to enrollment service?
def populate_assignments_for_student(enrollment):
    for a in enrollment.course.assignment_set.all():
        AssignmentService.create_student_assignment(a, enrollment)


def update_course_learners_count(course_id):
    from learning.models import Enrollment
    Course.objects.filter(id=course_id).update(
        learners_count=SubqueryCount(
            Enrollment.active.filter(course_id=OuterRef('id'))
        )
    )


def course_failed_by_student(course: Course, student, enrollment=None) -> bool:
    """Checks that student didn't fail the completed course"""
    from learning.models import Enrollment
    if course.is_open or not course.is_completed:
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


class GroupEnrollmentKeyError(Exception):
    pass


class StudentGroupService:
    @staticmethod
    def add(course: Course, branch: Branch):
        group, _ = (StudentGroup.objects.get_or_create(
            course_id=course.pk,
            type=StudentGroupTypes.BRANCH,
            branch_id=branch.pk,
            defaults={
                "name_ru": branch.name_ru,
                "name_en": branch.name_en,
            }))

    @staticmethod
    def remove(course: Course, branch: Branch):
        StudentGroup.objects.filter(course_id=course.pk,
                                    branch_id=branch.pk).delete()

    @staticmethod
    def resolve(course: Course, student: User, enrollment_key: str = None):
        """
        Returns the target or associated student group for the course.
        """
        if course.group_mode == StudentGroupTypes.BRANCH:
            # It's possible to miss student group here since student could be
            # added to the course through the admin interface without
            # checking all the requirements
            return (StudentGroup.objects
                    .filter(course=course, branch_id=student.branch_id)
                    .first())
        elif course.group_mode == StudentGroupTypes.MANUAL:
            try:
                return StudentGroup.objects.get(course=course,
                                                enrollment_key=enrollment_key)
            except StudentGroup.DoesNotExist:
                raise GroupEnrollmentKeyError
        elif course.group_mode == StudentGroupTypes.NO_GROUPS:
            return None


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
        Creates record for tracking student progress on assignment
        if the assignment is not restricted for the student's group.
        """
        restricted_to = list(sg.pk for sg in assignment.restrict_to.all())
        if restricted_to and enrollment.student_group_id not in restricted_to:
            return
        return cls._create_student_assignment(assignment, enrollment.student_id)

    @classmethod
    def _create_student_assignment(cls, assignment: Assignment, student_id):
        """
        Creates record for tracking student progress on assignment regardless
        of the assignment group settings.
        """
        obj, created = StudentAssignment.base.update_or_create(
            assignment=assignment, student_id=student_id,
            defaults={'deleted_at': None})
        return obj

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
            ~Q(student__status__in=StudentStatuses.inactive_statuses)
        ]
        restrict_to = list(sg.pk for sg in assignment.restrict_to.all())
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
        pks = (Enrollment.active
               .filter(*filters)
               .values_list("student_id", flat=True))
        for student_id in pks:
            sa = cls._create_student_assignment(assignment, student_id)
            # Note(Dmitry): we create notifications here instead of a separate
            # receiver because it's much more efficient than getting
            # StudentAssignment objects back one by one. It seems
            # reasonable that 2 * N INSERTs are better than .bulk_create
            # + N SELECTs + N INSERTs.
            notify_student_new_assignment(sa)

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
        restricted_to_groups = set(sg.pk for sg in assignment.restrict_to.all())
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
    def enroll(user: User, course: Course, reason_entry='', **attrs):
        if reason_entry:
            timezone = course.get_timezone()
            today = now_local(timezone).strftime(DATE_FORMAT_RU)
            reason_entry = Concat(Value(f'{today}\n{reason_entry}\n\n'),
                                  F('reason_entry'),
                                  output_field=TextField())
        with transaction.atomic():
            enrollment, created = (Enrollment.objects.get_or_create(
                student=user, course=course,
                defaults={'is_deleted': True}))
            if not enrollment.is_deleted:
                raise AlreadyEnrolled
            # Use sharable lock for concurrent enrollments if necessary to
            # control participants number. A blocking operation since `nowait`
            # is not used.
            if course.is_capacity_limited:
                locked = Course.objects.select_for_update().get(pk=course.pk)
            # Try to update state of the enrollment record to `active`
            filters = [Q(pk=enrollment.pk), Q(is_deleted=True)]
            if course.is_capacity_limited:
                learners_count = SubqueryCount(
                    Enrollment.active
                    .filter(course_id=OuterRef('course_id')))
                filters.append(Q(course__capacity__gt=learners_count))
            updated = (Enrollment.objects
                       .filter(*filters)
                       .update(**attrs,
                               is_deleted=False,
                               reason_entry=reason_entry))
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

    @staticmethod
    def leave(enrollment: Enrollment, reason_leave=''):
        update_fields = ['is_deleted']
        enrollment.is_deleted = True
        if reason_leave:
            timezone = enrollment.course.get_timezone()
            today = now_local(timezone).strftime(DATE_FORMAT_RU)
            enrollment.reason_leave = Concat(
                Value(f'{today}\n{reason_leave}\n\n'),
                F('reason_leave'),
                output_field=TextField())
            update_fields.append('reason_leave')
        with transaction.atomic():
            enrollment.save(update_fields=update_fields)


def notify_student_new_assignment(student_assignment):
    (AssignmentNotification(user_id=student_assignment.student_id,
                            student_assignment=student_assignment,
                            is_about_creation=True)
     .save())


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
