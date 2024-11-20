import django_rq

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("-q", "--queue", type=str, default="default")

    def handle(self, *args, **options):
        queue = django_rq.get_queue(options.get("queue"))
        registry = queue.scheduled_job_registry
        for job_id in registry.get_job_ids():
            registry.remove(job_id, delete_job=True)