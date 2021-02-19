import re

from django.core.management.commands import makemessages
from django.utils.translation import template as trans_real
from django_jinja.management.commands.makemessages import strip_whitespaces

EXTRA_KEYWORDS = [
    '--keyword=_p:1c,2'  # alias for pgettext_lazy
]


class Command(makemessages.Command):
    xgettext_options = makemessages.Command.xgettext_options + EXTRA_KEYWORDS

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
                makemessages.Command.xgettext_options[:] +
                ['--keyword=%s' % kwd for kwd in xgettext_keywords]
            )
        # super(Command, self).handle(*args, **options)

        # TODO: remove code below after upgrading to django-jinja > 2.7.0 and inherit from django-jinja command
        # https://github.com/niwinz/django-jinja/issues/272
        old_endblock_re = trans_real.endblock_re
        old_block_re = trans_real.block_re
        old_constant_re = trans_real.constant_re

        old_templatize = trans_real.templatize
        # Extend the regular expressions that are used to detect
        # translation blocks with an "OR jinja-syntax" clause.
        trans_real.endblock_re = re.compile(
            trans_real.endblock_re.pattern + '|' + r"""^-?\s*endtrans\s*-?$""")
        trans_real.block_re = re.compile(
            trans_real.block_re.pattern + '|' + r"""^-?\s*trans(?:\s+(?:no)?trimmed)?(?:\s+(?!'|")(?=.*?=.*?)|\s*-?$)""")
        trans_real.plural_re = re.compile(
            trans_real.plural_re.pattern + '|' + r"""^-?\s*pluralize(?:\s+.+|-?$)""")
        trans_real.constant_re = re.compile(r""".*?_\(((?:".*?(?<!\\)")|(?:'.*?(?<!\\)')).*?\)""")

        def my_templatize(src, origin=None, **kwargs):
            new_src = strip_whitespaces(src)
            return old_templatize(new_src, origin, **kwargs)

        trans_real.templatize = my_templatize

        try:
            super(Command, self).handle(*args, **options)
        finally:
            trans_real.endblock_re = old_endblock_re
            trans_real.block_re = old_block_re
            trans_real.templatize = old_templatize
            trans_real.constant_re = old_constant_re
