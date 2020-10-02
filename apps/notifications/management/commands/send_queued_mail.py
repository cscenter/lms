from django.utils.decorators import method_decorator
from post_office.management.commands.send_queued_mail import Command as BaseCommand

from core.locks import distributed_lock, get_shared_connection


class Command(BaseCommand):
    @method_decorator(distributed_lock('post-office-lock',
                                       timeout=150,
                                       get_client=get_shared_connection))
    def handle(self, *args, **options):
        super().handle(*args, **options)
