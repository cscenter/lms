import json
import logging
from datetime import timedelta
from hashlib import sha1
from typing import Any, Dict, Optional

from model_utils.fields import AutoLastModifiedField

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.utils import formats, timezone

from core.timezone import get_now_utc

logger = logging.getLogger(__name__)


def _get_task_hash(task_name: str, task_params: Dict[str, Any]):
    task_params = json.dumps(task_params)
    s = "%s%s" % (task_name, task_params)
    return sha1(s.encode('utf-8')).hexdigest()


class TaskManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset()

    def unlocked(self, now):
        max_run_time = Task.MAX_RUN_TIME
        qs = self.get_queryset()
        expires_at = now - timedelta(seconds=max_run_time)
        unlocked = Q(locked_by__isnull=True) | Q(locked_at__lt=expires_at)
        return qs.filter(unlocked)

    def locked(self, now):
        max_run_time = Task.MAX_RUN_TIME
        qs = self.get_queryset()
        expires_at = now - timedelta(seconds=max_run_time)
        locked = Q(locked_by__isnull=False) | Q(locked_at__gte=expires_at)
        return qs.filter(locked)

    def get_task(self, task_name, kwargs=None):
        kwargs = kwargs or {}
        task_params = {k: v for k, v in sorted(kwargs.items())}
        task_hash = _get_task_hash(task_name, task_params)
        qs = self.get_queryset()
        return qs.filter(task_hash=task_hash)

    def drop_task(self, task_name, kwargs=None):
        return self.get_task(task_name, kwargs).delete()


class Task(models.Model):
    MAX_RUN_TIME = 300  # in seconds

    created = models.DateTimeField(db_index=True, auto_now_add=True)
    modified = AutoLastModifiedField()
    # the "name" of the task/function to be run
    task_name = models.CharField(max_length=190, db_index=True)
    # the json encoded parameters to pass to the task
    task_params = models.JSONField(
        verbose_name="Task Parameters",
        blank=True,
        default=dict)
    # a sha1 hash of the name and params, to lookup already scheduled tasks
    task_hash = models.CharField(max_length=40, db_index=True)

    verbose_name = models.CharField(max_length=255, null=True, blank=True)

    # The time when the processing is finished (even with errors). It is equal
    # to `None` when the processing is still in progress.
    processed_at = models.DateTimeField(db_index=True, null=True, blank=True)
    # details of the error that occurred
    error = models.TextField(blank=True)

    # details of who's trying to run the task at the moment
    locked_by = models.CharField(max_length=64, db_index=True,
                                 null=True, blank=True)
    locked_at = models.DateTimeField(db_index=True, null=True, blank=True)

    creator_content_type = models.ForeignKey(
        ContentType, null=True, blank=True,
        related_name='background_task', on_delete=models.CASCADE
    )
    creator_object_id = models.PositiveIntegerField(null=True, blank=True)
    creator = GenericForeignKey('creator_content_type', 'creator_object_id')

    objects = TaskManager()

    class Meta:
        db_table = 'tasks'

    def __str__(self):
        return u'{}'.format(self.verbose_name or self.task_name)

    def save(self, **kwargs):
        # force NULL rather than empty string
        self.locked_by = self.locked_by or None
        return super().save(**kwargs)

    @property
    def is_failed(self):
        return self.is_completed and bool(self.error)

    @property
    def is_completed(self):
        return self.processed_at is not None

    @property
    def is_locked(self) -> bool:
        max_run_time = Task.MAX_RUN_TIME
        expires_at = get_now_utc() - timedelta(seconds=max_run_time)
        return self.locked_by is not None or self.locked_at >= expires_at

    def created_at_local(self, tz):
        dt = timezone.localtime(self.created, timezone=tz)
        return formats.date_format(dt, "SHORT_DATETIME_FORMAT")

    @property
    def status(self) -> str:
        if self.is_completed:
            return "error" if self.is_failed else "ok"
        elif self.locked_at:
            return "in progress"
        else:
            return "waiting"

    def lock(self, locked_by) -> Optional["Task"]:
        now = timezone.now()
        unlocked = Task.objects.unlocked(now).filter(pk=self.pk)
        updated = unlocked.update(locked_by=locked_by, locked_at=now)
        if updated:
            self.locked_by = locked_by
            self.locked_at = now
            return self
        return None

    def complete(self):
        self.processed_at = timezone.now()
        self.save()

    @classmethod
    def build(cls, task_name, kwargs=None, verbose_name=None, creator=None) -> "Task":
        kwargs = kwargs or {}
        # Recreate task params with sorted keys
        task_params = {k: v for k, v in sorted(kwargs.items())}
        task_hash = _get_task_hash(task_name, task_params)
        return cls(
            task_name=task_name,
            task_params=task_params,
            task_hash=task_hash,
            verbose_name=verbose_name,
            creator=creator)
