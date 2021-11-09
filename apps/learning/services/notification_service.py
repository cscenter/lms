from courses.models import CourseTeacher
from learning.models import (
    AssignmentComment, AssignmentNotification, AssignmentSubmissionTypes,
    CourseNewsNotification, Enrollment, StudentAssignment
)


# TODO: store it closer to services or here?
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


def create_notifications_about_new_submission(submission: AssignmentComment):
    from learning.services.personal_assignment_service import (
        resolve_assignees_for_personal_assignment
    )
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
        assignment = student_assignment.assignment
        try:
            assignees = [a.teacher_id for a in
                         resolve_assignees_for_personal_assignment(student_assignment=student_assignment)]
        except Enrollment.DoesNotExist:
            return None
        # Check teachers notification preferences
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
