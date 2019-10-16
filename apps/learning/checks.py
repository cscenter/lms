from django.apps import apps
from django.core.checks import register, Error


class Tags:
    lms = "lms"


def get_installed_app_index(app_name, app_configs):
    for i, ac in enumerate(app_configs.values()):
        if ac.name == app_name:
            return i
    return -1


@register(Tags.lms)
def check_dependencies(app_configs, **kwargs):
    if not apps.is_installed('learning'):
        return []
    errors = []
    app_dependencies = (
        ('courses', 101),
    )
    for app_name, error_code in app_dependencies:
        if not apps.is_installed(app_name):
            errors.append(Error(
                "'%s' must be in INSTALLED_APPS in order to use the "
                "learning application" % app_name,
                id='lms.E%d' % error_code,
            ))
    courses_app_index = get_installed_app_index('courses', apps.app_configs)
    lms_app_index = get_installed_app_index('learning', apps.app_configs)
    if lms_app_index <= courses_app_index:
        errors.append(Error(
            "'learning' app must be follow after 'courses' in INSTALLED_APPS "
            "in order to use it",
            id='lms.E501',
        ))
    return errors
