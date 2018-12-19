from django.db import models


# TODO: Add tests. Looks Buggy
class MonitorStatusField(models.ForeignKey):
    """
    Logging changes of another model field, stores link to the last change.
    Reset monitoring field value by log cls after log entry was added to DB.

    Args:
        logging_model (cls):
            Model responsible for logging.
        monitored (string):
            Monitored field name
        when (iter):
            If monitored field get values from `when` attribute, monitoring
            field updated. Defaults to None, allows all values. [Optional]
    """

    def __init__(self, *args, **kwargs):
        cls_name = self.__class__.__name__
        self.logging_model = kwargs.pop('logging_model', None)
        if not self.logging_model:
            raise TypeError('%s requires a "logging_model" argument' % cls_name)
        self.monitored = kwargs.pop('monitored', None)
        if not self.monitored:
            raise TypeError('%s requires a "monitor" argument' % cls_name)
        when = kwargs.pop('when', None)
        if when is not None:
            when = set(when)
        self.when = when
        super().__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        # Add attribute to model instance after initialization
        self._monitored_attrname = '_monitored_%s' % name
        models.signals.post_init.connect(self._save_initial, sender=cls)
        super().contribute_to_class(cls, name, **kwargs)

    def _save_initial(self, sender, instance, **kwargs):
        if self.monitored in instance.get_deferred_fields():
            return
        setattr(instance, self._monitored_attrname,
                self.get_monitored_value(instance))

    def get_monitored_value(self, instance):
        return getattr(instance, self.monitored)

    def pre_save(self, model_instance, add):
        monitored_prev = getattr(model_instance, self._monitored_attrname)
        monitored_current = self.get_monitored_value(model_instance)
        if monitored_prev != monitored_current:
            if self.when is None or monitored_current in self.when:
                log_model = self.create_log_entry(model_instance, add)
                setattr(model_instance, self.attname, log_model.pk)
                self._save_initial(model_instance.__class__, model_instance)
        return super().pre_save(model_instance, add)

    def create_log_entry(self, instance, new_model):
        if new_model:
            return False
        attrs = {self.monitored: self.get_monitored_value(instance)}
        instance_fields = [f.attname for f in instance._meta.fields]
        for field in self.logging_model._meta.fields:
            # Do not override PK
            if isinstance(field, models.AutoField):
                continue
            if field.attname not in instance_fields:
                continue
            attrs[field.attname] = getattr(instance, field.attname)
        model = self.logging_model(**attrs)
        model.prepare_fields(instance, self.attname)
        model.save()
        return model

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['monitored'] = self.monitored
        kwargs['logging_model'] = self.logging_model
        if self.when is not None:
            kwargs['when'] = self.when
        return name, path, args, kwargs
