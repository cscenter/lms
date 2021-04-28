"""
How to register and send new notification:
    1. Create new notification type in admin. Add notification code to
    notifications.constants.NOTIFICATION_TYPES

    2. Create module `notifications` in your app. Make sure your app added to
    django.conf.settings.INSTALLED_APPS or it won't be visible to registry.

    3. Decorate notification handler with `register`.
    Notification type should be instance of notification.types
    Handler class should be inherited from NotificationService.
        from notifications import types
        from notifications.decorators import register
        @register(notification_type=types.LOG)
        class NewNotification(NotificationService):
            # Implement all abstract classes
            pass

    4. Generate event for `notify` Signal with provided `notification_type`.
    Receiver of `notify` signal will dispatch your event to appropriate
    notification handler or throw an error.
        from notifications.signals import notify
        from notification import types
        notify.send(
            comment.author,  # actor
            type=types.LOG,  # notification type
            verb='added',
            description="new comment added",
            action_object=comment,  # The object linked to the action itself.
            target=report,  # The object to which the activity was performed.
            recipient=recipient)

        An example to clarify what is target/action/actor/verb:
            justquick (actor) closed (verb) issue 2 (object)
            on activity-stream (target) 12 hours ago

Internals overview:
    `notifications` app uses Django autodiscover feature to find all
    `notifications` modules among registered apps. On module importing,
    all notification handler classes decorated by `register` with
    valid notification type will be registered in global NotificationRegistry.
    After that you can send message to `notify` Signal with specified
    notification type and receiver of `notify` Signal already know, what
    to do with message, how process and queue it in DB.

Limitations:
    actor, action_object and target models should have PK as `int`

Lets enumerate all existing notifications for the moment:
    1. NEW_PROJECT_REPORT_COMMENT
    Student <actor> added <verb> comment <action_object> on
        "Report for project" <target>
            action_object - ReportComment
            target - Report
    2. NEW_PROJECT_REPORT
    Student <actor> sent <verb> Report <action_object> on project" <target>
        action_object - Report
        target - Project
    3. PROJECT_REPORTING_STARTED, PROJECT_REPORTING_ENDED
    Was sent notification <action_object> about the beginning of the
        reporting period <verb> for Semester <target> to Student <recipient>
            action_object - None/self
            target - Semester
    4. NEW_ASSIGNMENT_SUBMISSION_COMMENT
    Student <actor> added <verb> comment <action_object> on Assignment <target>
        action_object - AssignmentComment
        target - StudentAssignment
    5. NEW_ASSIGNMENT
    Teacher <actor> added new "Assignment" <action_object> on
        CourseOffering <target>
            action_object - Assignment
            target - Course
    6. ASSIGNMENT_DEADLINE_UPDATED
    Deadline has been changed <verb> on "Assignment" <action_object>
        for CourseOffering <target>
            action_object - Assignment
            target - Course
    7. NEW_ASSIGNMENT_NEWS
    Teacher <actor> published <verb> news <action_object> on
        Course Offering <target>
            action_object  - CourseNews
            target - Course
    8. NEW_ASSIGNMENT_SUBMISSION
    Student <actor> added <verb> submission <action_object> for
        Assignment <target>
            action_object - AssignmentComment
            target - Assignment
    9. PROJECT_REVIEWER_ENROLLED
    10. PROJECT_REPORT_COMPLETED
    11. PROJECT_REPORT_IN_REVIEW_STATE
    12. PROJECT_REPORT_REVIEW_COMPLETED

"""
import os
import sys
from enum import Enum

from django.utils.module_loading import autodiscover_modules

from notifications.constants import NOTIFICATION_TYPES


def autodiscover():
    from django.conf import settings

    from notifications.registry import registry

    autodiscover_modules('notifications', register_to=registry)

    if settings.DEBUG:
        try:
            if sys.argv[1] in ('runserver', 'runserver_plus'):
                names = ', '.join("{}: {}".format(str(n), cls.__class__) for
                                  n, cls in registry.items())
                print('notifications: Registered %d notification types (%s) '
                      '[pid: %d].' % (len(registry), names, os.getpid()))
        except IndexError:
            pass


DEFAULT_TYPES = ["EMPTY", "LOG"]
NotificationTypes = Enum(value='NotificationTypes',
                         names=(DEFAULT_TYPES + NOTIFICATION_TYPES))
