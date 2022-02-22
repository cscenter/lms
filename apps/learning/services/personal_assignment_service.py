import logging
from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db.models import (
    Case, Count, DateTimeField, F, IntegerField, Max, Min, When, Window
)
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from core.timezone import get_now_utc
from core.typings import assert_never
from core.utils import Empty, _empty
from courses.constants import AssigneeMode, AssignmentStatus
from courses.models import Assignment, CourseTeacher
from courses.selectors import personal_assignments_list
from grading.services import CheckerSubmissionService
from learning.models import (
    AssignmentComment, AssignmentScoreAuditLog, AssignmentSubmissionTypes, Enrollment,
    PersonalAssignmentActivity, StudentAssignment
)
from learning.services import StudentGroupService
from learning.settings import AssignmentScoreUpdateSource
from users.models import User

logger = logging.getLogger(__name__)


def update_personal_assignment_stats(*, personal_assignment: StudentAssignment) -> None:
    """
    Calculates personal assignment stats and saves it in a `stats` property
    of the .meta json field.

    Full Example:
        {
            "comments": 1,
            "solutions": {
                "count": 3,
                "first": "2020-11-03T19:38:44Z", // datetime of the first submission
                "last": "2020-11-03T19:39:44Z"
            },
            "activity": "sc",  // code of the latest activity
        }
    """
    solutions_count = Count(
        Case(When(type=AssignmentSubmissionTypes.SOLUTION,
                  then=1),
             output_field=IntegerField()))
    solution_first = Min(
        Case(When(type=AssignmentSubmissionTypes.SOLUTION,
                  then=F('created')),
             output_field=DateTimeField()))
    solution_latest = Max(
        Case(When(type=AssignmentSubmissionTypes.SOLUTION,
                  then=F('created')),
             output_field=DateTimeField()))
    window = {
        'partition_by': [F('student_assignment_id')],
        'order_by': F('created').asc()
    }
    latest_submission = (AssignmentComment.published
                         .filter(student_assignment_id=personal_assignment.pk)
                         .annotate(submissions_total=Window(expression=Count('*'), **window),
                                   solutions_total=Window(expression=solutions_count, **window),
                                   solution_first=Window(expression=solution_first, **window),
                                   solution_latest=Window(expression=solution_latest, **window))
                         .order_by('created')
                         .last())
    if latest_submission is None:
        return

    if latest_submission.type == AssignmentSubmissionTypes.SOLUTION:
        latest_activity = PersonalAssignmentActivity.SOLUTION
    elif latest_submission.type == AssignmentSubmissionTypes.COMMENT:
        is_student = latest_submission.author_id == personal_assignment.student_id
        if is_student:
            latest_activity = PersonalAssignmentActivity.STUDENT_COMMENT
        else:
            latest_activity = PersonalAssignmentActivity.TEACHER_COMMENT
    else:
        raise ValueError('Unknown submission type')
    # Django 3.2 doesn't support partial update of the json field,
    # better to select_for_update
    meta = personal_assignment.meta or {}
    new_stats = {'activity': str(latest_activity)}
    comments_total = latest_submission.submissions_total - latest_submission.solutions_total
    if comments_total:
        new_stats['comments'] = comments_total
    # Omit default or null values to save space
    if latest_submission.solutions_total:
        solution_stats = {
            'count': latest_submission.solutions_total,
            'first': latest_submission.solution_first.replace(microsecond=0),
        }
        if latest_submission.solutions_total > 1:
            solution_stats['last'] = latest_submission.solution_latest.replace(microsecond=0)
        new_stats['solutions'] = solution_stats
    meta['stats'] = new_stats
    (StudentAssignment.objects
     .filter(pk=personal_assignment.pk)
     .update(meta=meta))


def create_assignment_solution(*, personal_assignment: StudentAssignment,
                               created_by: User,
                               execution_time: Optional[timedelta] = None,
                               message: Optional[str] = None,
                               attachment: Optional[UploadedFile] = None) -> AssignmentComment:
    if not message and not attachment:
        raise ValidationError("Provide either text or a file.", code="malformed")
    meta = {
        'score_old': personal_assignment.score,
        'score': personal_assignment.score,
        'status_old': personal_assignment.status,
        'status': AssignmentStatus.ON_CHECKING
    }
    solution = AssignmentComment(student_assignment=personal_assignment,
                                 author=created_by,
                                 type=AssignmentSubmissionTypes.SOLUTION,
                                 is_published=True,
                                 execution_time=execution_time,
                                 text=message,
                                 meta=meta,
                                 attached_file=attachment)
    solution.save()
    update_personal_assignment_status(student_assignment=personal_assignment,
                                      status_old=AssignmentStatus(personal_assignment.status),
                                      status_new=AssignmentStatus.ON_CHECKING)
    from learning.tasks import update_student_assignment_stats
    update_student_assignment_stats.delay(personal_assignment.pk)

    return solution


# TODO: Looks like a good example for signal (save additional checker settings
#  to the StudentAssignment.meta, then move checker part to the grading app?)
def create_assignment_solution_and_check(*, personal_assignment: StudentAssignment,
                                         created_by: User, settings: Dict[str, Any],
                                         execution_time: Optional[timedelta] = None,
                                         attachment: Optional[UploadedFile] = None) -> AssignmentComment:
    """Creates assignment solution along with a checker submission."""
    solution = create_assignment_solution(personal_assignment=personal_assignment,
                                          created_by=created_by, execution_time=execution_time,
                                          message='', attachment=attachment)
    CheckerSubmissionService.update_or_create(solution, **settings)
    return solution


def create_assignment_comment(*, personal_assignment: StudentAssignment,
                              is_draft: bool, created_by: User,
                              message: Optional[str] = None,
                              attachment: Optional[UploadedFile] = None,
                              meta: Optional[Dict[str, Any]] = None) -> AssignmentComment:
    if meta is None:
        if not (message or attachment):
            raise ValidationError(_("Either text or file should be non-empty"),
                                  code='malformed')
    else:
        score = meta.get('score', _empty)
        status = meta.get('status', None)
        values = (message, attachment, score is not _empty, status is not None)
        if not any(values):
            msg = _("At least one of text, file, meta.score, meta.status must be provided")
            raise ValidationError(msg, code='malformed')
        if not is_draft:
            if 'score_old' in meta:
                if not (meta['score_old'] is None or isinstance(meta['score_old'], Decimal)):
                    raise ValidationError("Wrong old status value in meta", code='malformed')
            elif score is not _empty:
                raise ValidationError("Missing old score value in meta", code='malformed')
            if 'status_old' in meta:
                try:
                    AssignmentStatus(meta['status_old'])
                except ValueError:
                    raise ValidationError("Wrong old status value in meta", code='malformed')
            elif status is not None:
                raise ValidationError("Missing old status value in meta", code='malformed')

    comment = get_draft_comment(created_by, personal_assignment)
    if comment is None:
        comment = AssignmentComment(student_assignment=personal_assignment,
                                    author=created_by,
                                    type=AssignmentSubmissionTypes.COMMENT)
    comment.is_published = not is_draft
    comment.text = message
    comment.attached_file = attachment
    comment.created = get_now_utc()  # TODO: write test
    if meta is not None:
        comment.meta = {
            **(comment.meta or {}),
            **meta
        }
    comment.save()

    from learning.tasks import update_student_assignment_stats
    update_student_assignment_stats.delay(personal_assignment.pk)

    return comment


def _get_draft_submission(user: User,
                          student_assignment: StudentAssignment,
                          submission_type) -> Optional[AssignmentComment]:
    """Returns draft submission if it was previously saved."""
    return (AssignmentComment.objects
            .filter(author=user,
                    is_published=False,
                    type=submission_type,
                    student_assignment=student_assignment)
            .order_by('pk')
            .last())


def get_draft_comment(user: User, student_assignment: StudentAssignment):
    return _get_draft_submission(user, student_assignment,
                                 AssignmentSubmissionTypes.COMMENT)


def get_draft_solution(user: User, student_assignment: StudentAssignment):
    return _get_draft_submission(user, student_assignment,
                                 AssignmentSubmissionTypes.SOLUTION)


def update_personal_assignment_status(*, student_assignment: StudentAssignment,
                                      status_old: AssignmentStatus,
                                      status_new: AssignmentStatus) -> bool:
    if not student_assignment.is_status_transition_allowed(status_new):
        raise ValidationError(f"Wrong status {status_new} for student assignment", code="status_not_allowed")
    updated = (StudentAssignment.objects
               .filter(pk=student_assignment.pk, status=status_old)
               .update(status=status_new, modified=get_now_utc()))
    if updated:
        student_assignment.status = status_new
    return updated


def update_personal_assignment_score(*, student_assignment: StudentAssignment,
                                     changed_by: User, source: AssignmentScoreUpdateSource,
                                     score_old: Optional[Decimal],
                                     score_new: Optional[Decimal]) -> Tuple[bool, StudentAssignment]:
    if score_new is not None and score_new > student_assignment.assignment.maximum_score:
        raise ValidationError(f"Score {score_new} is greater than the maximum "
                              f"score {student_assignment.assignment.maximum_score}",
                              code="score_overflow")

    updated = (StudentAssignment.objects
               .filter(pk=student_assignment.pk, score=score_old)
               .update(score=score_new, score_changed=get_now_utc()))
    if not updated:
        return False, student_assignment

    student_assignment.score = score_new
    if score_new != score_old:
        audit_log = AssignmentScoreAuditLog(student_assignment=student_assignment,
                                            changed_by=changed_by,
                                            score_old=score_old,
                                            score_new=score_new,
                                            source=source)
        audit_log.save()

    return True, student_assignment


def create_personal_assignment_review(*, student_assignment: StudentAssignment,
                                      reviewer: User,
                                      is_draft: bool,
                                      score_old: Optional[Decimal],
                                      score_new: Optional[Decimal],
                                      status_old: AssignmentStatus,
                                      status_new: AssignmentStatus,
                                      source: AssignmentScoreUpdateSource,
                                      message: Optional[str] = None,
                                      attachment: Optional[UploadedFile] = None,
                                      ) -> AssignmentComment:
    """
    Updates assignment score and/or status on publishing review,
    posts a new comment in a published or draft state.

    New comment on publishing review stores log of the score and status
    changes in a .meta field.
    """
    is_score_changed = score_new != score_old
    is_status_changed = status_new != status_old
    has_comment = message or attachment
    if not (has_comment or is_score_changed or is_status_changed):
        raise ValidationError(_("Nothing to process"), code='empty')
    meta = {
        "score": score_new,
        "status": status_new
    }
    if not is_draft:
        meta['score_old'] = score_old
        meta['status_old'] = status_old
        msg = _("The score or status has been changed by someone. "
                "Review the changes to resolve the conflict.")
        updated, sa = update_personal_assignment_score(student_assignment=student_assignment,
                                                       changed_by=reviewer,
                                                       score_old=score_old,
                                                       score_new=score_new,
                                                       source=source)
        if not updated:
            raise ValidationError(msg, code="concurrent")
        updated = update_personal_assignment_status(student_assignment=sa,
                                                    status_old=status_old,
                                                    status_new=status_new)
        if not updated:
            raise ValidationError(msg, code="concurrent")
    comment = create_assignment_comment(personal_assignment=student_assignment,
                                        created_by=reviewer,
                                        is_draft=is_draft,
                                        message=message,
                                        attachment=attachment,
                                        meta=meta)
    return comment


# TODO: remove
def update_student_assignment_derivable_fields(comment):
    """
    Optimize db queries by reimplementing next logic:
        student_assignment.compute_fields('first_student_comment_at')
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
    StudentAssignment.objects.filter(pk=sa.pk).update(**fields)
    for attr_name, attr_value in fields.items():
        setattr(sa, attr_name, attr_value)


def resolve_assignees_for_personal_assignment(student_assignment: StudentAssignment) -> List[CourseTeacher]:
    """
    Returns candidates who can be auto-assign as a responsible teacher for the
    personal assignment.
    """
    if student_assignment.assignee_id is not None:
        return [student_assignment.assignee]

    assignment = student_assignment.assignment
    assignee_mode = assignment.assignee_mode
    if assignee_mode == AssigneeMode.DISABLED:
        return []
    elif assignee_mode == AssigneeMode.MANUAL:
        return list(assignment.assignees.all())
    elif assignee_mode in {AssigneeMode.STUDENT_GROUP_DEFAULT, AssigneeMode.STUDENT_GROUP_CUSTOM}:
        try:
            enrollment = (Enrollment.active
                          .select_related('student_group')
                          .get(course_id=assignment.course_id,
                               student_id=student_assignment.student_id))
        except Enrollment.DoesNotExist:
            logger.info(f"User {student_assignment.student_id} has left the course.")
            raise
        if assignee_mode == AssigneeMode.STUDENT_GROUP_CUSTOM:
            return StudentGroupService.get_assignees(enrollment.student_group, assignment)
        elif assignee_mode == AssigneeMode.STUDENT_GROUP_DEFAULT:
            return StudentGroupService.get_assignees(enrollment.student_group)
    else:
        assert_never(assignee_mode)


def maybe_set_assignee_for_personal_assignment(submission: AssignmentComment) -> None:
    """
    This handler helps to assign responsible teacher for the personal
    assignment when any student activity occurs.
    """
    student_assignment = submission.student_assignment
    # Trigger on student activity
    if submission.author_id != student_assignment.student_id:
        return None
    if not student_assignment.trigger_auto_assign:
        return None
    update_fields = ['trigger_auto_assign', 'modified']
    # Do not overwrite assignee if someone already set the value.
    if not student_assignment.assignee_id:
        try:
            assignees = resolve_assignees_for_personal_assignment(student_assignment)
        except Enrollment.DoesNotExist:
            # Left auto assigning trigger until student re-enter the course.
            return None
        if assignees:
            if len(assignees) == 1:
                update_fields.append('assignee')
                assignee = assignees[0]
                student_assignment.assignee = assignee
            else:
                # It is unclear who must be set as an assignee in that case.
                # Let's leave it blank to send notifications to all responsible
                # teachers until they decide who must be assigned.
                # TODO: set all of them as watchers instead
                pass
    student_assignment.trigger_auto_assign = False
    student_assignment.modified = now()
    student_assignment.save(update_fields=update_fields)


def get_personal_assignments_by_enrollment_id(*, assignment: Assignment) -> Dict[str, StudentAssignment]:
    """
    Returns map of enrollment ID to personal assignment for the *assignment*.
    Takes into account active course students only.
    """
    enrollments_ = (Enrollment.active
                    .filter(course_id=assignment.course_id)
                    .values("student_id", "pk"))
    enrollments = {e['student_id']: e['pk'] for e in enrollments_}
    filters = {"assignments": [assignment.pk]}
    student_assignments = list(personal_assignments_list(filters=filters)
                               .only("pk", "score", "student_id"))
    by_enrollment = {}
    for sa in student_assignments:
        if sa.student_id in enrollments:
            sa.assignment = assignment
            enrollment_id = enrollments[sa.student_id]
            by_enrollment[str(enrollment_id)] = sa
    return by_enrollment


def get_personal_assignments_by_yandex_login(*, assignment: Assignment) -> Dict[str, StudentAssignment]:
    """
    Returns personal assignments of students that provided yandex login
    in their account.
    """
    filters = {"assignments": [assignment.pk]}
    student_assignments = list(personal_assignments_list(filters=filters)
                               .select_related('student')
                               .only("pk", "score", "student__yandex_login_normalized"))
    with_yandex_login = {}
    for sa in student_assignments:
        yandex_login = sa.student.yandex_login_normalized
        if yandex_login:
            sa.assignment = assignment
            with_yandex_login[str(yandex_login)] = sa
    return with_yandex_login


def get_personal_assignments_by_stepik_id(*, assignment: Assignment) -> Dict[str, StudentAssignment]:
    """
    Returns personal assignments of students that provided stepik ID in
    their account.
    """
    filters = {"assignments": [assignment.pk]}
    student_assignments = list(personal_assignments_list(filters=filters)
                               .select_related('student')
                               .only("pk", "score", "student__stepic_id"))
    with_stepik_id = {}
    for sa in student_assignments:
        stepik_id = sa.student.stepic_id
        if stepik_id:
            sa.assignment = assignment
            with_stepik_id[str(stepik_id)] = sa
    return with_stepik_id


def get_assignment_update_history_message(comment: AssignmentComment) -> str:
    if not isinstance(comment.meta, dict):
        return ""
    score_new = comment.meta.get('score', None)
    score_old = comment.meta.get('score_old', None)
    is_score_changed = score_old != score_new
    status_new = comment.meta.get('status', None)
    status_old = comment.meta.get('status_old', None)
    is_status_changed = status_old != status_new
    if score_new is None:
        score_new = "без оценки"
    status_label = AssignmentStatus(status_new).label
    text = ''
    if is_score_changed and is_status_changed:
        text = f"Выставлена новая оценка: <code>{score_new}</code> и новый статус: {status_label}."
    elif is_score_changed:
        text = f"Выставлена новая оценка: <code>{score_new}</code>"
    elif is_status_changed:
        text = f"Выставлен новый статус: {status_label}"
    return text
