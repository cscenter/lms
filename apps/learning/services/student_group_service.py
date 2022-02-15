from typing import Any, Dict, List, Optional, Tuple

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from core.models import Branch
from core.typings import assert_never
from core.utils import bucketize
from courses.constants import AssigneeMode
from courses.models import (
    Assignment, Course, CourseGroupModes, CourseTeacher, StudentGroupTypes
)
from courses.services import CourseService
from learning.models import (
    AssignmentGroup, CourseClassGroup, Enrollment, Invitation, StudentGroup,
    StudentGroupAssignee
)
from learning.services.assignment_service import AssignmentService
from users.models import StudentProfile, StudentTypes

CourseTeacherId = int
StudentGroupId = int


class StudentGroupError(Exception):
    pass


class GroupEnrollmentKeyError(StudentGroupError):
    pass


class StudentGroupService:
    @staticmethod
    def create(course: Course, *, group_type: str, **attrs: Any) -> StudentGroup:
        if course.group_mode == CourseGroupModes.NO_GROUPS:
            raise StudentGroupError(f"Course group mode {course.group_mode} "
                                    f"does not support student groups")
        if group_type == StudentGroupTypes.BRANCH:
            branch: Branch = attrs.pop('branch', None)
            if branch not in course.branches.all():
                raise ValidationError(f"Branch {branch} must be a course branch", code="malformed")
            group, _ = (StudentGroup.objects.get_or_create(
                type=group_type,
                course_id=course.pk,
                branch_id=branch.pk,
                defaults={
                    "name_ru": branch.name_ru,
                    "name_en": branch.name_en,
                    **attrs,
                }))
            return group
        elif group_type == StudentGroupTypes.INVITE:
            invitation: Invitation = attrs.pop('invitation')
            if invitation.semester_id != course.semester_id:
                raise ValidationError("Invitation semester does not match course semester",
                                      code="malformed")
            # TODO: provide explicit array of valid fields for attrs.
            group = StudentGroup(
                **attrs,
                type=group_type,
                course=course,
                invitation=invitation,
                name=invitation.name)
            group.save()
            return group
        elif group_type == StudentGroupTypes.MANUAL:
            group_name = attrs.pop('name', None)
            if not group_name:
                raise ValidationError('Provide a unique non-empty name', code='required')
            group = StudentGroup(
                **attrs,
                course_id=course.pk,
                type=StudentGroupTypes.MANUAL,
                name=group_name)
            group.save()
            return group
        else:
            assert_never(group_type)

    @staticmethod
    def update(student_group: StudentGroup, *, name: str):
        student_group.name = name
        student_group.save()

    @classmethod
    def remove(cls, student_group: StudentGroup):
        # If this is the only one group presented in assignment restriction
        # settings after deleting it the assignment would be considered as
        # "available to all" - that's not really what we want to achieve.
        # The same is applied to CourseClass restriction settings.
        in_assignment_settings = (AssignmentGroup.objects
                                  .filter(group=student_group))
        in_class_settings = (CourseClassGroup.objects
                             .filter(group=student_group))
        active_students = (Enrollment.active
                           .filter(student_group=student_group))
        # XXX: This action will be triggered after removing course branch
        if student_group.type == StudentGroupTypes.BRANCH:
            cast_to_manual = (active_students.exists() or
                              in_assignment_settings.exists() or
                              in_class_settings.exists())
            if cast_to_manual:
                student_group.type = StudentGroupTypes.MANUAL
                student_group.branch = None
                student_group.save()
            else:
                cls._move_unenrolled_students_to_default_group(student_group)
                student_group.delete()
        elif student_group.type == StudentGroupTypes.MANUAL:
            if active_students.exists():
                raise ValidationError("Students are attached to the student group")
            if in_assignment_settings.exists():
                raise ValidationError("Student group is a part of assignment restriction settings")
            if in_class_settings.exists():
                raise ValidationError("Student group is a part of class restriction settings")

            cls._move_unenrolled_students_to_default_group(student_group)
            student_group.delete()

    @classmethod
    def _move_unenrolled_students_to_default_group(cls, student_group: StudentGroup):
        """Transfers students who left the course to the default system group"""
        default_group = cls.get_or_create_default_group(student_group.course)
        (Enrollment.objects
         .filter(course_id=student_group.course_id,
                 is_deleted=True,
                 student_group=student_group)
         .update(student_group=default_group))

    @classmethod
    def resolve(cls, course: Course, *, student_profile: StudentProfile,
                invitation: Optional[Invitation] = None,
                enrollment_key: Optional[str] = None):
        """Returns the target student group for unenrolled student."""
        # Invitation has the highest priority even if the course group mode
        # doesn't support invites.
        # Use case: Regular students divide by branch, but students
        # enrolled by the specific invitation link (others could be ignored)
        # go to the student group associated with this invitation.
        if invitation is not None and student_profile.type == StudentTypes.INVITED:
            student_group = (StudentGroup.objects
                             .filter(course=course,
                                     type=StudentGroupTypes.INVITE,
                                     invitation=invitation)
                             .first())
            if student_group is not None:
                return student_group
        if (course.group_mode == CourseGroupModes.BRANCH or
                course.group_mode == CourseGroupModes.INVITE_AND_BRANCH):
            if course.group_mode == CourseGroupModes.INVITE_AND_BRANCH:
                if invitation is not None and student_profile.type == StudentTypes.INVITED:
                    student_group, created = StudentGroup.objects.get_or_create(
                        course=course,
                        type=StudentGroupTypes.INVITE,
                        invitation=invitation,
                        defaults={
                            "name": invitation.name,
                        })
                    return student_group
            student_group = (StudentGroup.objects
                             .filter(course=course,
                                     type=StudentGroupTypes.BRANCH,
                                     branch_id=student_profile.branch_id)
                             .first())
            # Student could be enrolled in the course through the admin
            # interface without meeting the branch requirements. In that case
            # add them to the special group
            if student_group is None:
                student_group = cls.get_or_create_default_group(course)
            return student_group
        elif course.group_mode == CourseGroupModes.MANUAL:
            if enrollment_key:
                try:
                    return StudentGroup.objects.get(course=course,
                                                    type=StudentGroupTypes.MANUAL,
                                                    enrollment_key=enrollment_key)
                except StudentGroup.DoesNotExist:
                    # In fact, there is no enrollment key support right now
                    msg = _("Please, check your group enrollment key")
                    raise GroupEnrollmentKeyError(msg)
            else:
                student_group = cls.get_or_create_default_group(course)
                return student_group
        raise StudentGroupError(f"Course group mode {course.group_mode} is not supported")

    @staticmethod
    def get_or_create_default_group(course: Course) -> StudentGroup:
        """
        Logically this student group means "No Group" or NULL in terms of DB.

        Each student must be associated with a student group, but it's
        impossible to always know the target group.
        E.g. on enrollment it's impossible to always know in advance the
        target group or on deleting group student must be transferred
        to some group to meet the requirements.
        """
        student_group, _ = StudentGroup.objects.get_or_create(
            course=course,
            type=StudentGroupTypes.SYSTEM,
            branch_id__isnull=True,
            invitation_id__isnull=True,
            defaults={
                "name_en": "Others",
                "name_ru": "Другие"
            })
        return student_group

    @staticmethod
    def unique_sites(student_groups: List[StudentGroup]) -> int:
        """Returns number of unique sites where student groups are available."""
        sites = set()
        for g in student_groups:
            if g.branch_id:
                g.branch = Branch.objects.get_by_pk(g.branch_id)
                sites.add(g.branch.site_id)
        return len(sites) if sites else 1

    @classmethod
    def get_choices(cls, course: Course) -> List[Tuple[int, str]]:
        choices = []
        student_groups = CourseService.get_student_groups(course)
        sites_total = cls.unique_sites(student_groups)
        for g in student_groups:
            label = g.get_name(branch_details=sites_total > 1)
            choices.append((g.pk, label))
        return choices

    @staticmethod
    def add_assignees(student_group: StudentGroup, *,
                      assignment: Assignment = None,
                      teachers: List[CourseTeacher]) -> None:
        """Assigns new responsible teachers to the student group."""
        new_objects = []
        for teacher in teachers:
            fields = {
                "student_group": student_group,
                "assignee": teacher,
                "assignment": assignment if assignment else None
            }
            new_objects.append(StudentGroupAssignee(**fields))
        # Validate records before call .bulk_create()
        for sga in new_objects:
            sga.full_clean()
        StudentGroupAssignee.objects.bulk_create(new_objects)

    @classmethod
    def update_assignees(cls, student_group: StudentGroup, *,
                         teachers: List[CourseTeacher],
                         assignment: Assignment = None) -> None:
        """
        Set default list of responsible teachers for the student group or
        customize list of teachers for the *assignment* if value is provided.
        """
        current_assignees = set(StudentGroupAssignee.objects
                                .filter(student_group=student_group,
                                        assignment=assignment)
                                .values_list('assignee_id', flat=True))
        to_delete = []
        new_assignee_ids = {course_teacher.pk for course_teacher in teachers}
        for group_assignee_id in current_assignees:
            if group_assignee_id not in new_assignee_ids:
                to_delete.append(group_assignee_id)
        # TODO: try to overwrite records before deleting
        (StudentGroupAssignee.objects
         .filter(student_group=student_group,
                 assignment=assignment,
                 assignee__in=to_delete)
         .delete())
        to_add = [course_teacher for course_teacher in teachers
                  if course_teacher.pk not in current_assignees]
        cls.add_assignees(student_group, assignment=assignment, teachers=to_add)

    @staticmethod
    def get_assignees(student_group: StudentGroup,
                      assignment: Assignment = None) -> List[CourseTeacher]:
        """
        Returns list of responsible teachers. If *assignment* value is provided
        could return list of teachers specific for this assignment or
        default one for the student group.
        """
        default_and_overridden = Q(assignment__isnull=True)
        if assignment:
            default_and_overridden |= Q(assignment=assignment)
        assignees = list(StudentGroupAssignee.objects
                         .filter(default_and_overridden,
                                 student_group=student_group)
                         # FIXME: order by
                         .select_related('assignee__teacher'))
        # Teachers assigned for the particular assignment fully override
        # default list of the teachers assigned on the course level
        if any(ga.assignment_id is not None for ga in assignees):
            # Remove defaults
            assignees = [ga for ga in assignees if ga.assignment_id]
        filtered = [ga.assignee for ga in assignees]
        return filtered

    # FIXME: move to assignment service? it depends on assignee mode :<
    # FIXME: add tests
    @staticmethod
    def set_custom_assignees_for_assignment(*, assignment: Assignment,
                                            data: Dict[StudentGroupId, List[CourseTeacherId]]) -> None:
        if assignment.assignee_mode != AssigneeMode.STUDENT_GROUP_CUSTOM:
            raise ValidationError(f"Change assignee mode first to customize student group "
                                  f"responsible teachers for assignment {assignment}")
        to_add = []
        for student_group_id, assignee_list in data.items():
            for assignee_id in assignee_list:
                obj = StudentGroupAssignee(assignment=assignment,
                                           student_group_id=student_group_id,
                                           assignee_id=assignee_id)
                to_add.append(obj)
        StudentGroupAssignee.objects.filter(assignment=assignment).delete()
        StudentGroupAssignee.objects.bulk_create(to_add)

    @staticmethod
    def get_student_profiles(student_group: StudentGroup) -> List[StudentProfile]:
        """
        Returns student profiles of users enrolled in the course.

        Note:
            Profiles are sorted by the student's last name.
        """
        return list(StudentProfile.objects
                    .filter(enrollment__is_deleted=False,
                            enrollment__student_group=student_group)
                    .select_related('user')
                    .order_by('user__last_name'))

    @staticmethod
    def get_groups_available_for_student_transfer(source_group: StudentGroup) -> List[StudentGroup]:
        """
        Returns list of target student groups where students of the source
        student group could be transferred to.
        """
        student_groups = list(StudentGroup.objects
                              .filter(course_id=source_group.course_id)
                              .exclude(pk=source_group.pk)
                              .select_related('branch__site')
                              .order_by('name'))
        # Deleting existing personal assignments is forbidden. This means it's
        # not possible to transfer a student to a target group if any
        # assignment available in the source group but not available in
        # the target group.
        all_target_groups = {sg.pk for sg in student_groups}
        available_groups = all_target_groups.copy()
        qs = (AssignmentGroup.objects
              .filter(group__course_id=source_group.course_id))
        assignment_settings = bucketize(qs, key=lambda ag: ag.assignment_id)
        for bucket in assignment_settings.values():
            groups = {ag.group_id for ag in bucket}
            if source_group.pk not in groups:
                groups = all_target_groups
            available_groups &= groups
        return [sg for sg in student_groups if sg.pk in available_groups]

    @staticmethod
    def available_assignments(student_group: StudentGroup) -> List[Assignment]:
        """
        Returns list of course assignments available for the *student_group*.
        """
        available = []
        assignments = (Assignment.objects
                       .filter(course_id=student_group.course_id)
                       .prefetch_related('restricted_to'))
        for assignment in assignments:
            restricted_to_groups = assignment.restricted_to.all()
            if not restricted_to_groups or student_group in restricted_to_groups:
                available.append(assignment)
        return available

    @classmethod
    def transfer_students(cls, *, source: StudentGroup, destination: StudentGroup,
                          student_profiles: List[int]) -> None:
        if source.course_id != destination.course_id:
            raise ValidationError("Invalid destination", code="invalid")
        safe_transfer_to = cls.get_groups_available_for_student_transfer(source)
        if destination not in safe_transfer_to:
            raise ValidationError("Invalid destination", code="unsafe")
        (Enrollment.objects
         .filter(course=source.course,
                 student_group=source,
                 student_profile__in=student_profiles)
         .update(student_group_id=destination))
        # After students were transferred to the target group create missing
        # personal assignments
        source_group_assignments = cls.available_assignments(source)
        target_group_assignments = cls.available_assignments(destination)
        # Assignments that are not available in the source group, but
        # available in the target group
        in_target_group_only = set(target_group_assignments).difference(source_group_assignments)
        # Create missing personal assignments
        for assignment in in_target_group_only:
            AssignmentService.bulk_create_student_assignments(assignment=assignment,
                                                              for_groups=[destination.pk])

