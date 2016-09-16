from rq import Worker
from django.db import connection


class CustomRQWorker(Worker):
    """
    Use it in management command using `--worker-class` param, for example:
    ```
    ./manage.py rqworker --worker-class=core.queue.CustomRQWorker default
    ```
    """
    def perform_job(self, *args, **kwargs):
        """
        Handles connection (wait) timeouts on RQ.
        Solution below fixes this bug by closing connections before and after
        each job on worker and forcing Django to open a new one.
        Resources:
        * https://github.com/translate/pootle/issues/4094
        * http://dev.mysql.com/doc/refman/5.7/en/gone-away.html
        * https://dev.mysql.com/doc/refman/5.7/en/error-lost-connection.html
        """
        connection.close_if_unusable_or_obsolete()
        result = super(CustomRQWorker, self).perform_job(*args, **kwargs)
        connection.close_if_unusable_or_obsolete()
        return result
