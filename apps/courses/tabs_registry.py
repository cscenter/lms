class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class CourseTabRegistry:
    def __init__(self):
        self._registry = {}

    def register(self, tab_class, **options):
        """
        Registers the given tab type.
        If tab already registered, this will raise AlreadyRegistered.
        """

        if tab_class.type in self._registry:
            raise AlreadyRegistered(
                f'The tab {tab_class.type} is already registered.')
        self._registry[tab_class.type] = tab_class

    def unregister(self, tab_type):
        """
        Unregisters the given tab type.

        If a type isn't already registered, this will raise NotRegistered.
        """
        if tab_type not in self._registry:
            raise NotRegistered('The type %s is not registered' % tab_type)
        del self._registry[tab_type.name]

    def __contains__(self, model):
        return model in self._registry

    def __len__(self):
        return len(self._registry)

    def __iter__(self):
        return self._registry

    def __getitem__(self, model):
        return self._registry[model]

    def registered_types(self):
        return self._registry.keys()

    def items(self):
        return self._registry.items()


registry = CourseTabRegistry()


def register(tab_class):
    """Simple class decorator for registering tab classes"""
    registry.register(tab_class)
    return tab_class
