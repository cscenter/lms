from django.db.models import FileField


class ConfigurableStorageFileField(FileField):
    """
    Ignores the `storage` attribute when creating migrations.

    Storage class can be selected depending on settings (the default locally,
    remote in production), but django migrations will hard-code the class
    on serialization. Looks like it's safe to remove this attribute to avoid
    messing up with migrations.
    """
    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.pop('storage', None)
        return name, path, args, kwargs
