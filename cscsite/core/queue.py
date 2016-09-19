from rq import Worker
from django.db import close_old_connections


class CustomRQWorker(Worker):
    """
    Do the actual work in a fail-safe context, but make sure first that
    db connection is still alive.

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
        close_old_connections()
        result = super(CustomRQWorker, self).perform_job(*args, **kwargs)
        close_old_connections()
        return result
