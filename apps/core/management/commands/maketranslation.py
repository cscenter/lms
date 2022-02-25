from django_jinja.management.commands import makemessages

EXTRA_KEYWORDS = [
    '--keyword=_p:1c,2'  # alias for pgettext_lazy
]


class Command(makemessages.Command):
    # TODO: Command in django-stubs lacks xgettext_options.
    xgettext_options = makemessages.Command.xgettext_options + EXTRA_KEYWORDS  # type: ignore[attr-defined]

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--extra-keyword',
            dest='xgettext_keywords',
            action='append',
        )

    def handle(self, *args, **options):
        xgettext_keywords = options.pop('xgettext_keywords')
        if xgettext_keywords:
            self.xgettext_options = (
                makemessages.Command.xgettext_options[:] +  # type: ignore[attr-defined]
                ['--keyword=%s' % kwd for kwd in xgettext_keywords]
            )
        super(Command, self).handle(*args, **options)
