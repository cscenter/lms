import ast

from django.core.management.base import AppCommand, CommandError

from core.db.mixins import DerivableFieldsMixin


class Command(AppCommand):
    help = "Updates derivable fields"

    def add_arguments(self, parser):
        parser.add_argument('args', metavar='app_label', nargs='+',
                            help='One application label.')
        parser.add_argument(dest='model_name', type=str, action='store',
                            help='Django model name with derivable fields.')
        parser.add_argument('-n', dest='field_names', action='append',
                            help='Specify property names to compute')
        parser.add_argument('-m', dest='custom_manager', type=str,
                            default='objects', action='store',
                            help='Customize model manager name.')
        parser.add_argument('-f', dest='queryset_filters', type=str,
                            action='append',
                            help='Customize one or more filters for queryset. '
                                 'Usage examples: '
                                 ' -f due_date__isnull=True -f id__in=[86]')

    def handle_app_config(self, app_config, **options):
        model_name = options['model_name']
        model = app_config.get_model(model_name)
        if not issubclass(model, DerivableFieldsMixin):
            raise CommandError(f"{model.__name__} model needs subclass of "
                               f"DerivableFieldsMixin")

        derivable_fields = options['field_names'] or []
        custom_manager = getattr(model, options['custom_manager'] or 'objects')
        queryset_filters = options['queryset_filters']

        if queryset_filters:
            queryset_filters = {
                field: ast.literal_eval(value) for f in queryset_filters
                for field, value in [f.split('=')]
            }
            custom_manager = custom_manager.filter(**queryset_filters)
        custom_manager = custom_manager.order_by()

        count = 0
        # TODO: replace with `core.utils.queryset_iterator`
        for model_object in custom_manager.iterator():
            count += int(model_object.compute_fields(*derivable_fields,
                                                     prefetch=True))
            # TODO: pause?

        self.stdout.write(f'Updated {model_name} objects: {count}')
