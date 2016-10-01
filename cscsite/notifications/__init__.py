"""
How it works:
    `notifications` app uses Django autodiscover feature to find all
    notifications module in registered app. When `notifications` module
    imported, all signal handlers decorated by `register` will be
    registered in global NotificationRegistry. After that you can send
    message to `notify` Signal with specified `notification_uid` and receiver
    of `notify` Signal already know, what to do with message, how process
    and queue it in DB.

How to register and send new notification:
    1. Create module `notifications` in your app. Make sure app in your
    django.conf.settings.INSTALLED_APPS

    2. Create notification id, unique among all your apps. Registry do some
    checks to make sure notification uid is really unique among all
    projects notification uids. If it's not - an error will be raised.
        from notifications.decorators import NotificationType
        class Type(NotificationType):
            NEW_UID = 4  # must be int

    3. Decorate signal handler with `register`. Make sure notification_uid arg
    is instance of NotificationType or you will get an error.
        from notifications.decorators import register
        @register(notification_uid=Type.NEW_UID)
        def signal_handler(*args, **kwargs):
            # Handler should know how to generate message and add it to the db
            pass

    4. Generate event for `notify` Signal with provided `notifiction_uid`.
    Receiver of `notify` signal will dispatch your event to appropriate signal
    handler or throw an error.
        from notifications.signals import notify
        notify.send(
            comment.author,  # actor
            type=Type.NEW_UID,
            verb='added',
            description="new comment added",
            action_object=comment,  # The object linked to the action itself.
            target=report,  # The object to which the activity was performed.
            recipient=recipient)

An example to clarify what is target/action/actor/verb:
    justquick (actor) closed (verb) issue 2 (object)
    on activity-stream (target) 12 hours ago

Limitations:
    actor, action_object and target models should have PK as `int`

Lets enumerate all existing notifications for the moment:
    1. Student <actor> added <verb> comment <action_object> on
        "Report for project" <target>
            action_object - ReportComment
            target - Report
    2. Student <actor> sent <verb> Report <action_object> on project" <target>
        action_object - Report
        target - Project
    3. Was sent notification <action_object> about the beginning of the
        reporting period <verb> for Semester <target> to Student <recipient>
            action_object - None/self
            target - Semester
    4. Student <actor> added <verb> comment <action_object> on Assignment <target>
        action_object - AssignmentComment
        target - StudentAssignment
    5. Teacher <actor> added new "Assignment" <action_object> on
        CourseOffering <target>
            action_object - Assignment
            target - CourseOffering
    6. Deadline has been changed <verb> on "Assignment" <action_object>
        for CourseOffering <target>
            action_object - Assignment
            target - CourseOffering
    7. Teacher <actor> published <verb> news <action_object> on
        Course Offering <target>
            action_object  - CourseOfferingNews
            target - CourseOffering
    8. Student <actor> added <verb> submission <action_object> for
        Assignment <target>
            action_object - AssignmentComment
            target - Assignment
"""
import os
import sys
from django.utils.module_loading import autodiscover_modules

from notifications.registry import registry


def autodiscover():
    from django.conf import settings

    autodiscover_modules('notifications', register_to=registry)

    if settings.DEBUG:
        try:
            if sys.argv[1] in ('runserver', 'runserver_plus'):
                names = ', '.join("{}: {}".format(str(n), f.__name__) for n, f
                                  in registry.items())
                print('notifications: Registered %d type notifications (%s) '
                      '[pid: %d].' % (len(registry), names, os.getpid()))
        except IndexError:
            pass
