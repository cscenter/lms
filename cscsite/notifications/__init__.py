"""
In most this module inspired by
https://github.com/django-notifications/django-notifications

An example how to add notification to queue:
    from notifications.signals import notify

    notify.send(
        comment.author,  # actor
        verb='added',
        description="new comment added",
        action_object=comment,  # The object linked to the action itself.
        target=report,  # The object to which the activity was performed.
        recipient=recipient)

Other example to clarify what is target/action/actor/verb:
    justquick (actor) closed (verb) issue 2 (object)
    on activity-stream (target) 12 hours ago

Set `target` only if you have no action object, e.g. report status was updated.

Limitations:
    actor, action_object and target models should have PK as `int`

Existing notifications:
    # TODO: specify recipients
    1. Student <actor> added <verb> comment <action_object> on
        "Report for project" <target>
        action_object - ReportComment
        target - Report
    2. Student <actor> sent <verb> Report <action_object> on project" <target>
        action_object - Report
        target - Project
    3. Was sent notification <action_object> about the beginning of the
        reporting period <verb> for project <target> to Student <recipient>
        target - Project
        action_object - None
    4. Student <actor> added <verb> comment <action_object> on Assignment <target>
        action_object - AssignmentComment
        target - StudentAssignment
    5. Teacher <actor> added new "Assignment" <action_object> on
            CourseOffering <target>
            action_object - Assignment
            target - CourseOffering
    6. Deadline has been changed <verb> on "Assignment" <action_object>
        for CourseOffering <target>

    7. Teacher <actor> published <verb> news <action_object> on
            Course Offering <target>
    8. Student <actor> added <verb> submission <action_object> for
            Assignment <target>
"""
import os
import sys
from django.utils.module_loading import autodiscover_modules

from notifications.notifier import notifier


def autodiscover():
    from django.conf import settings

    autodiscover_modules('notifications', register_to=notifier)

    if settings.DEBUG:
        try:
            if sys.argv[1] in ('runserver', 'runserver_plus'):
                configs = notifier.get_registered_configs()
                names = ', '.join(c.__name__ for c in configs)
                print('notifications: Registered %d configs (%s) [pid: %d].' %
                      (len(configs), names, os.getpid()))
        except IndexError:
            pass
