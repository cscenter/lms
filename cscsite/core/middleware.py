"""
https://gist.github.com/1ddc318b4124ed152f6d.git
Django middleware for generating request flame graphs.
Requires the flamegraph.pl perl script:
https://github.com/brendangregg/FlameGraph/blob/master/flamegraph.pl

Installation:
1. Create a directory for flame graphs
2. Copy the flamegraph.pl script to it
3. Add the FLAMES_DIR django setting
4. Add the flames.FlamesMiddleware to MIDDLEWARE_CLASSES

Usage:
To generate a flame graph just append ?flames to the requested url.
Middleware will create an svg in the FLAMES_DIR with the current timestamp.

Uncomment line 158 to automatically open the svg in a new google chrome tab.
Note: `runserver` with --noreload --nothreading parameters
"""

from datetime import datetime
import os
import signal
import subprocess
import sys
import time
from xml.dom.minidom import Text

from django.conf import settings


class StackLogger(object):
    interval = 0.0005
    handlers = set()

    def __init__(self, ignore_below=[]):
        self.ignore_below = set(ignore_below)

    @classmethod
    def add_handler(cls, handler):
        cls.handlers.add(handler)

        if len(cls.handlers) == 1:
            signal.setitimer(signal.ITIMER_PROF, cls.interval, cls.interval)
            signal.signal(signal.SIGPROF, cls.signal_router)

    @classmethod
    def remove_handler(cls, handler):
        if len(cls.handlers) == 0:
            return

        cls.handlers.discard(handler)

        if len(cls.handlers) == 0:
            signal.setitimer(signal.ITIMER_PROF, 0, 0)
            signal.signal(signal.SIGPROF, signal.SIG_IGN)

    @classmethod
    def signal_router(cls, signum, frame):
        for handler in cls.handlers:
            handler(signum, frame)

    @classmethod
    def get_module_name(cls, module_path):
        for path in sys.path:
            path = path or os.getcwd()

            if module_path.startswith(path):
                rel_path = module_path[len(path) + 1:]

                return (
                    rel_path
                    .replace(u'/__init__.py', u'')
                    .replace(u'/', '.')
                    .replace(u'.py', u'')
                    .strip()
                )

        return None

    def start(self):
        self.samples = []
        self.add_handler(self.signal_handler)

    def stop(self):
        self.remove_handler(self.signal_handler)

    def signal_handler(self, signum, frame):
        stack = []
        while frame:
            code = frame.f_code
            module_name = self.get_module_name(code.co_filename)

            stack.append((
                code.co_filename,
                module_name,
                code.co_name
            ))

            if (module_name, code.co_name) in self.ignore_below:
                break

            frame = frame.f_back

        stack = list(reversed(stack))
        self.samples.append((time.clock(), stack))

    def write(self, f):
        for t, stack in self.samples:
            stack_str = u';'.join(
                u'{}@{}'.format(func_name, module_name)
                for module_path, module_name, func_name in stack
            )
            f.write(u'{} {}\n'.format(stack_str, 1))


class FlamesMiddleware(object):
    def process_request(self, request):
        if settings.DEBUG and 'flames' in request.GET:
            logger = StackLogger(
                ignore_below=[('django.core.handlers.base', 'get_response')]
            )
            logger.start()
            request._stack_logger = logger

    def process_response(self, request, response):
        if settings.DEBUG and hasattr(request, '_stack_logger'):
            request._stack_logger.stop()

            url = request.build_absolute_uri()
            now = datetime.now()

            out_filename = (
                u'{time:%Y-%m-%dT%H:%M:%S}'
                .format(url=url, time=now)
            )

            out_dir = os.path.abspath(
                getattr(settings, 'FLAMES_DIR') or
                os.path.join(settings.PROJECT_PATH, u'..', u'log', u'flames')
            )

            flamegraph_script_path = os.path.join(out_dir, 'flamegraph.pl')
            out_txt_path = os.path.join(out_dir, out_filename) + '.txt'
            out_svg_path = os.path.join(out_dir, out_filename) + '.svg'

            title_element = Text()
            title_element.data = url

            with open(out_txt_path, 'w') as out_txt, open(out_svg_path, 'w') as out_svg:
                request._stack_logger.write(out_txt)
                subprocess.call(
                    [
                        'perl', flamegraph_script_path, out_txt_path,
                        '--title', title_element.toxml(),
                    ],
                    stdout=out_svg
                )
            print out_svg_path
            # subprocess.call(['google-chrome', 'file://' + out_svg_path])

        return response
