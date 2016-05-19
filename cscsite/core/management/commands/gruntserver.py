import os
import subprocess
import atexit
import signal

from django.conf import settings
from django.contrib.staticfiles.management.commands.runserver import Command \
    as RunserverCommand


# TODO: investigate django-grunt
class Command(RunserverCommand):

    def inner_run(self, *args, **options):
        self.start_grunt()
        return super(Command, self).inner_run(*args, **options)

    def start_grunt(self):
        self.stdout.write('>>> Starting grunt with {0}/Gruntfile.js'.format(
            settings.ROOT_DIR))
        # TODO: implement and rewrite Gruntfile.js
        """ Use os.environ.copy() to get a copy of the current env, and
        then set a new key on the object with the STATICFILES_DIR as the
        value. Then, pass that object as the "env" kwarg for
        subprocess.Popen. Now, in your Gruntfile you can use
        the Node.js process.env object to retrieve your variable."""
        grunt_process = subprocess.Popen(
            ['grunt --gruntfile={0}/Gruntfile.js --base=.'.format(
                settings.ROOT_DIR)],
            shell=True,
            stdin=subprocess.PIPE,
            stdout=self.stdout,
            stderr=self.stderr,
        )

        self.stdout.write('>>> Grunt process on pid {0}'.format(
            grunt_process.pid))

        def kill_grunt_process(pid):
            self.stdout.write('>>> Closing grunt process')
            os.kill(pid, signal.SIGTERM)

        atexit.register(kill_grunt_process, grunt_process.pid)
