from abc import ABC, ABCMeta, abstractmethod, abstractproperty
from collections import Iterable


class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class NotificationConfig(object):
    __metaclass__ = ABCMeta
    # BACKEND = None

    @abstractproperty
    def template(self):
        pass

    @abstractmethod
    def get_notifications(self):
        pass

    @abstractmethod
    def notify(self, notification):
        template = "template"
        context = self.get_context(notification)

    @abstractmethod
    def get_context(self, notification):
        return {}


class Notifier(object):
    """
    A Notifier object encapsulates an instance of the notifications application
    and used for sending notifications to recipients.
    Models are registered with the Notifier using the register() method.
    """
    def __init__(self):
        # TODO: replace with set? Looks like I don't need options
        self._registry = {}

    def register(self, config_class, **options):
        """
        Registers the given config class with the given options.
        If a config is already registered, this will raise AlreadyRegistered.
        """

        if config_class in self._registry:
            raise AlreadyRegistered(
                'The config %s is already registered' % config_class.__name__)

        # For reasons I don't quite understand, without a __module__
        # the created class appears to "live" in the wrong place,
        # which causes issues later on.
        options['__module__'] = __name__
        # TODO: Not sure it's really necessary. Need to invent useful example
        opts_class = type("%sConfig" % config_class.__name__, (config_class,),
                          options)
        opts = opts_class()
        self._registry[config_class] = opts

    def unregister(self, config_or_iterable):
        """
        Unregisters the given config(s).

        If a model isn't already registered, this will raise NotRegistered.
        """
        if not isinstance(config_or_iterable, Iterable):
            config_or_iterable = [config_or_iterable]
        for config in config_or_iterable:
            if config not in self._registry:
                raise NotRegistered(
                    'The config %s is not registered' % config.__name__)
            del self._registry[config]

    def is_registered(self, config):
        """
        Check if a config class is registered with this `Notifier`.
        """
        return config in self._registry

    def get_registered_configs(self):
        return self._registry

notifier = Notifier()
