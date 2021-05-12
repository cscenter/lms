from django.conf import settings
from django.template import Library, Node

register = Library()


class AppOrderNode(Node):
    """
        Reorders the app_list and child model lists on the admin index page.
    """
    def render(self, context):
        if 'app_list' in context:
            for app_label, app_models in settings.ADMIN_REORDER:
                for app_orig in context['app_list']:
                    if app_orig['app_label'] == app_label:
                        model_list = list(app_orig['models'])
                        models_ordered = []
                        # look at models in user order
                        for model_name in app_models:
                            # look at models in orig order
                            for model in model_list:
                                if model['object_name'] == model_name:
                                    models_ordered.append(model)
                                    app_orig['models'].remove(model)
                                    break
                        models_ordered[len(models_ordered):] = app_orig['models']
                        app_orig["models"] = models_ordered
                        break
        return ''


@register.tag
def admin_reorder(parser, token):
    return AppOrderNode()
