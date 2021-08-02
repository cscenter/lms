from django.apps import apps
from django.conf import settings
from django.dispatch import Signal
from django.utils import timezone

from notifications.registry import NotRegistered, registry

# The providing_args argument is deprecated. Let's store it in a comment for
# documentation purposes.
# providing_args=[
#     'type', 'recipient', 'actor', 'verb', 'action_object',
#     'target', 'description', 'timestamp', 'level'
# ]
notify = Signal()


EXTRA_DATA = getattr(settings, 'NOTIFICATIONS_USE_JSONFIELD', False)


def notify_handler(type, **kwargs):
    """
    Dispatch data to appropriate signal handler based on notification type
    """
    from django.contrib.contenttypes.models import ContentType

    from notifications import NotificationTypes
    from notifications.models import Notification
    from users.models import Group, User

    if not isinstance(type, NotificationTypes):
        raise ValueError("Notification type must be an instance "
                         "of NotificationType cls")

    # If we haven't handler for registered notification - save it in db anyway
    if type in registry:
        notification_service = registry[type]
    else:
        notification_service = registry.default_handler_class()

    type_map = apps.get_app_config('notifications').type_map
    try:
        type_id = type_map[type.name]
    except KeyError:
        raise NotRegistered('Notification type %s is not registered in DB' %
                            type.name)

    # Pull the options out of kwargs
    kwargs.pop('signal', None)
    recipient = kwargs.pop('recipient')
    actor = kwargs.pop('sender', None)
    optional_objs = [
        (kwargs.pop(opt, None), opt)
        for opt in ('target', 'action_object')
    ]
    public = bool(kwargs.pop('public', True))
    description = kwargs.pop('description', None)
    timestamp = kwargs.pop('timestamp', timezone.now())
    level = kwargs.pop('level', Notification.LevelTypes.info)
    data = kwargs.pop('data', None)
    verb = kwargs.pop('verb', None)

    # Check if User or Group
    if isinstance(recipient, Group):
        recipients = recipient.user_set.all()
    elif isinstance(recipient, User):
        recipients = [recipient]
    else:
        recipients = [None]

    for recipient in recipients:
        new_notification = Notification(
            type_id=type_id,
            recipient=recipient,
            verb=str(verb),
            public=public,
            description=description,
            timestamp=timestamp,
            level=level,
            data=data,
        )

        # Make an actor optional too. But it's little bit complicated due
        # to an actor object retrieves from `sender`
        if actor is not None:
            setattr(new_notification, 'actor_object_id', actor.pk)
            setattr(new_notification, 'actor_content_type',
                    ContentType.objects.get_for_model(actor))
        # Set optional objects
        for obj, opt in optional_objs:
            if obj is not None:
                setattr(new_notification, '%s_object_id' % opt, obj.pk)
                setattr(new_notification, '%s_content_type' % opt,
                        ContentType.objects.get_for_model(obj))

        if len(kwargs) and EXTRA_DATA:
            new_notification.data = kwargs

        notification_service.add_to_queue(new_notification, **kwargs)
