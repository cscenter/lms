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
