from datetime import timedelta
from itertools import islice
from typing import Iterable, List, Optional, Union

from django.core.files.uploadedfile import UploadedFile
from django.db import router
from django.db.models import Avg, Q

from core.services import SoftDeleteService
from courses.models import Assignment, AssignmentAttachment, CourseTeacher
from learning.models import (
    AssignmentNotification, Enrollment, StudentAssignment, StudentGroup
)
from learning.services.notification_service import notify_student_new_assignment
from learning.settings import StudentStatuses


class AssignmentService:
    @staticmethod
    def process_attachments(assignment: Assignment,
                            attachments: List[UploadedFile]):
        if attachments:
            for attachment in attachments:
                (AssignmentAttachment.objects
                 .create(assignment=assignment, attachment=attachment))

    @staticmethod
    def set_responsible_teachers(assignment: Assignment, *, teachers: List[int]) -> None:
        assignment.assignees.clear()
        assignment.assignees.add(*teachers)

    @classmethod
    def create_or_restore_student_assignment(cls, assignment: Assignment,
                                             enrollment: Enrollment) -> Optional[StudentAssignment]:
        """
        Creates or restores record for tracking student progress on assignment
        if the assignment is not restricted for the student's group.
        """
        restricted_to = list(sg.pk for sg in assignment.restricted_to.all())
        if restricted_to and enrollment.student_group_id not in restricted_to:
            return None
        student_assignment, _ = StudentAssignment.base.update_or_create(
            assignment=assignment, student_id=enrollment.student_id,
            # FIXME: is it really necessary to reset score and execution_time?
            defaults={'deleted_at': None, 'score': None, 'execution_time': None})
        return student_assignment

    @classmethod
    def _restore_student_assignments(cls, assignment: Assignment,
                                     student_ids: Iterable[int]):
        qs = (StudentAssignment.trash
              .filter(assignment=assignment, student_id__in=student_ids))
        for student_assignment in qs:
            # TODO: reset score? execution_time?
            student_assignment.restore()

    # TODO: send notification to teachers
    @classmethod
    def bulk_create_student_assignments(cls, assignment: Assignment,
                                        for_groups: Iterable[Union[int, None]] = None):
        """
        Generates personal assignments to store student progress.
        By default it creates record for each enrolled student who's not
        expelled or on academic leave and the assignment is available for
        the student group in which the student participates in the course.

        You can process students from the specific groups only by setting
        `for_groups`. Special value `for_groups=[..., None]` - includes
        enrollments without student group.
        """
        filters = [
            Q(course_id=assignment.course_id),
            ~Q(student_profile__status__in=StudentStatuses.inactive_statuses)
        ]
        restrict_to = list(sg.pk for sg in assignment.restricted_to.all())
        # Filter out enrollments not in the targeted course groups
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
            filters.append(Q(student_group_id__in=restrict_to))
        students = list(Enrollment.active
                        .filter(*filters)
                        .values_list("student_id", flat=True))
        # Records could exist in case of transferring students from one
        # group to another
        already_exist = set(StudentAssignment.objects
                            .filter(assignment=assignment, student__in=students)
                            .values_list('student_id', flat=True))
        # Restore personal assignments
        in_trash = set(StudentAssignment.trash
                       .filter(assignment=assignment, student__in=students)
                       .values_list('student_id', flat=True))
        if in_trash:
            cls._restore_student_assignments(assignment, in_trash)
        # Create personal assignments if necessary
        already_created = already_exist | in_trash
        batch_size = 100
        to_create = (sid for sid in students if sid not in already_created)
        objs = (StudentAssignment(assignment=assignment, student_id=student_id)
                for student_id in to_create)
        while True:
            batch = list(islice(objs, batch_size))
            if not batch:
                break
            StudentAssignment.objects.bulk_create(batch, batch_size)
        # TODO: move to the separated method
        # Generate notifications
        to_notify = [sid for sid in students if sid not in already_exist]
        created = (StudentAssignment.objects
                   .filter(assignment=assignment, student_id__in=to_notify)
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
        # XXX: It could skip processing the whole student group if someone
        # manually created personal assignment for student from this group.
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
    def get_median_execution_time(cls, assignment: Assignment):
        queryset = (StudentAssignment.objects
                    .filter(assignment=assignment)
                    .exclude(execution_time__isnull=True))
        count = queryset.count()
        if not count:
            return None
        # TODO: perf: combine with queryset.count()
        values = (queryset
                  .values_list('execution_time', flat=True)
                  .order_by('execution_time'))
        if count % 2 == 1:
            return values[count // 2]
        else:
            mid = count // 2
            return sum(values[mid - 1:mid + 1], timedelta()) / 2
