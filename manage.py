#!/usr/bin/env python
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
sys.path.append(str(ROOT_DIR / "apps/"))


if __name__ == "__main__":
    # On production use --settings to override default behavior
    os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                          "compscicenter_ru.settings.local")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
