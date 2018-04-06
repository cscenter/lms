from datetime import timedelta
from hashlib import sha1
import json
import logging

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.utils import timezone
from model_utils.fields import AutoLastModifiedField

logger = logging.getLogger(__name__)


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

    def get_task(self, task_name, args=None, kwargs=None):
        args = args or ()
        kwargs = kwargs or {}
        task_params = json.dumps((args, kwargs), sort_keys=True)
        s = "%s%s" % (task_name, task_params)
        task_hash = sha1(s.encode('utf-8')).hexdigest()
        qs = self.get_queryset()
        return qs.filter(task_hash=task_hash)

    def drop_task(self, task_name, args=None, kwargs=None):
        return self.get_task(task_name, args, kwargs).delete()


class Task(models.Model):
    MAX_RUN_TIME = 300  # in seconds

    created = models.DateTimeField(db_index=True, auto_now_add=True)
    modified = AutoLastModifiedField()  # TODO: when this field can be really useful?
    # the "name" of the task/function to be run
    task_name = models.CharField(max_length=190, db_index=True)
    # the json encoded parameters to pass to the task
    task_params = models.TextField()
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

    def save(self, *args, **kwargs):
        # force NULL rather than empty string
        self.locked_by = self.locked_by or None
        return super(Task, self).save(*args, **kwargs)

    def is_failed(self):
        return bool(self.error)

    def params(self):
        args, kwargs = json.loads(self.task_params)
        # need to coerce kwargs keys to str
        kwargs = dict((str(k), v) for k, v in kwargs.items())
        return args, kwargs

    def lock(self, locked_by):
        now = timezone.now()
        unlocked = Task.objects.unlocked(now).filter(pk=self.pk)
        updated = unlocked.update(locked_by=locked_by, locked_at=now)
        if updated:
            self.locked_by = locked_by
            self.locked_at = now
            return self
        return None

    @classmethod
    def build(cls, task_name, args=None, kwargs=None,
              verbose_name=None, creator=None):
        args = args or ()
        kwargs = kwargs or {}
        task_params = json.dumps((args, kwargs), sort_keys=True)
        s = "%s%s" % (task_name, task_params)
        task_hash = sha1(s.encode('utf-8')).hexdigest()
        return cls(
            task_name=task_name,
            task_params=task_params,
            task_hash=task_hash,
            verbose_name=verbose_name,
            creator=creator)
