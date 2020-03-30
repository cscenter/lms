import datetime

from django.utils import timezone

from core.timezone.typing import Timezone


def now_local(tz: Timezone) -> datetime.datetime:
    return timezone.localtime(timezone.now(), timezone=tz)
