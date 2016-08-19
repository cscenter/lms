# -*- coding: utf-8 -*-

_UNSAVED_FILE_SUPERVISOR_PRESENTATION = 'unsaved_supervisor_presentation'
_UNSAVED_FILE_PRESENTATION = 'unsaved_presentation'


def pre_save_project(sender, instance, **kwargs):
    """
    Save presentation files when project model already created and we can
    get project pk.
    """
    if not instance.pk:
        if not hasattr(instance, _UNSAVED_FILE_SUPERVISOR_PRESENTATION):
            setattr(instance, _UNSAVED_FILE_SUPERVISOR_PRESENTATION,
                    instance.supervisor_presentation)
            instance.supervisor_presentation = None
        if not hasattr(instance, _UNSAVED_FILE_PRESENTATION):
            setattr(instance, _UNSAVED_FILE_PRESENTATION,
                    instance.presentation)
            instance.presentation = None


def post_save_project(sender, instance, created, *args, **kwargs):
    if created:
        save = False
        if hasattr(instance, _UNSAVED_FILE_SUPERVISOR_PRESENTATION):
            instance.supervisor_presentation = getattr(
                instance,
                _UNSAVED_FILE_SUPERVISOR_PRESENTATION
            )
            instance.__dict__.pop(_UNSAVED_FILE_SUPERVISOR_PRESENTATION)
            save = True
        if hasattr(instance, _UNSAVED_FILE_PRESENTATION):
            instance.presentation = getattr(instance,
                                            _UNSAVED_FILE_PRESENTATION)
            instance.__dict__.pop(_UNSAVED_FILE_PRESENTATION)
            save = True
        if save:
            instance.save()
