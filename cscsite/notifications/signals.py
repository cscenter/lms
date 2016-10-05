from django.conf import settings
from django.dispatch import Signal
from django.utils import timezone
from django.utils.six import text_type

from notifications.registry import registry, NotRegistered

notify = Signal(providing_args=[
    'type', 'recipient', 'actor', 'verb', 'action_object',
    'target', 'description', 'timestamp', 'level'
])


EXTRA_DATA = getattr(settings, 'NOTIFICATIONS_USE_JSONFIELD', False)

NOTIFICATION_TYPES_MAP = None


def notify_handler(type, **kwargs):
    """
    Dispatch data to appropriate signal handler based on notification type
    """
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import Group
    from notifications import types
    from notifications.models import Type, Notification
    from users.models import CSCUser

    if not isinstance(type, types):
        raise ValueError("Notification type must be an instance "
                         "of NotificationType cls")

    # If we haven't handler for registered notification - save it in db anyway
    if type in registry:
        notification_service = registry[type]
    else:
        notification_service = registry.default_handler_class()

    # Cache types translation
    # FIXME: think where to move this init code. Can use this in notify management command too.
    global NOTIFICATION_TYPES_MAP
    if NOTIFICATION_TYPES_MAP is None:
        NOTIFICATION_TYPES_MAP = {t.code: t.id for t in Type.objects.all()}
    try:
        type_id = NOTIFICATION_TYPES_MAP[type.name]
    except KeyError:
        raise NotRegistered('Notification type %s is not registered in DB' %
                            type.name)

    # Pull the options out of kwargs
    kwargs.pop('signal', None)
    recipient = kwargs.pop('recipient')
    actor = kwargs.pop('sender')
    optional_objs = [
        (kwargs.pop(opt, None), opt)
        for opt in ('target', 'action_object')
    ]
    public = bool(kwargs.pop('public', True))
    description = kwargs.pop('description', None)
    timestamp = kwargs.pop('timestamp', timezone.now())
    level = kwargs.pop('level', Notification.LEVELS.info)
    data = kwargs.pop('data', None)
    verb = kwargs.pop('verb', None)

    # Check if User or Group
    if isinstance(recipient, Group):
        recipients = recipient.user_set.all()
    elif isinstance(recipient, CSCUser):
        recipients = [recipient]
    else:
        recipients = [None]

    for recipient in recipients:
        new_notification = Notification(
            type_id=type_id,
            recipient=recipient,
            actor_content_type=ContentType.objects.get_for_model(actor),
            actor_object_id=actor.pk,
            verb=text_type(verb),
            public=public,
            description=description,
            timestamp=timestamp,
            level=level,
            data=data,
        )

        # Set optional objects
        for obj, opt in optional_objs:
            if obj is not None:
                setattr(new_notification, '%s_object_id' % opt, obj.pk)
                setattr(new_notification, '%s_content_type' % opt,
                        ContentType.objects.get_for_model(obj))

        if len(kwargs) and EXTRA_DATA:
            new_notification.data = kwargs

        notification_service.add_to_queue(new_notification, **kwargs)
