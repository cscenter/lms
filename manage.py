#!/usr/bin/env python
import os
import sys

sys.path.append(os.path.abspath("cscsite/"))

if __name__ == "__main__":
    # On production use --settings to override default behavior
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cscenter.settings.local")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
