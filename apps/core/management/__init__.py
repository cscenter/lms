from django.apps import apps as global_apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.color import no_style
from django.db import DEFAULT_DB_ALIAS, connections, router


def create_default_city_branch_user(app_config, verbosity=2, interactive=True, using=DEFAULT_DB_ALIAS, apps=global_apps, **kwargs):
    try:
        City = apps.get_model('core', 'City')
    except LookupError:
        return

    if not router.allow_migrate_model(using, City):
        return

    if not City.objects.using(using).exists():
        # It isn't guaranteed that the next id will be 1, so coerce it
        if verbosity >= 2:
            print("Creating default City object")
        City(code=settings.DEFAULT_CITY_CODE,
             name='Санкт-Петербург', abbr='СПб',
             time_zone='Europe/Moscow').save(using=using)

    try:
        Branch = apps.get_model('core', 'Branch')
    except LookupError:
        return

    if not router.allow_migrate_model(using, City):
        return

    if not Branch.objects.using(using).exists():
        # It isn't guaranteed that the next id will be 1, so coerce it
        if verbosity >= 2:
            print("Creating default City object")
        Branch(pk=1, code=settings.DEFAULT_BRANCH_CODE,
               name='Главное отделение',
               city_id=settings.DEFAULT_CITY_CODE, site_id=1,
               time_zone='Europe/Moscow').save(using=using)

        # We set an explicit pk instead of relying on auto-incrementation,
        # so we need to reset the database sequence. See #17415.
        sequence_sql = connections[using].ops.sequence_reset_sql(no_style(), [Branch])
        if sequence_sql:
            if verbosity >= 2:
                print("Resetting sequence")
            with connections[using].cursor() as cursor:
                for command in sequence_sql:
                    cursor.execute(command)
