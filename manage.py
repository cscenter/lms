#!/usr/bin/env python
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
# XXX: Note that location of the `manage.py` is fixed.
# It's placement hasn't been changed for years so looks like it's not a problem.
sys.path.append(str(ROOT_DIR / "apps/"))
sys.path.append(str(ROOT_DIR / "compscicenter_ru" / "apps"))


if __name__ == "__main__":
    # On production use --settings to override default behavior
    os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                          "compscicenter_ru.settings.local")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
