# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import posixpath
import sys
from lxml import html
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

from django.db import models, migrations


def extract_youtube_url(pk, html_source):
    html_tree = html.fromstring(html_source)
    iframes = html_tree.xpath("//iframe[contains(@src, 'youtube.com/embed')]")
    if not iframes:
        print("{:03d} no embed found".format(pk), file=sys.stderr)
        print(html_source, file=sys.stderr)
        return
    elif len(iframes) > 1:
        print("{:03d}: multiple embeds found".format(pk), file=sys.stderr)
        print(html_source, file=sys.stderr)
        return

    [iframe] = iframes
    return iframe.attrib["src"].rstrip("/")


def forwards(apps, schema_editor):
    count = 0
    CourseClass = apps.get_model('learning', 'CourseClass')
    q = (models.Q(video__contains="youtube") |
         models.Q(other_materials__contains="youtube"))
    course_classes = CourseClass.objects.filter(q)
    for course_class in course_classes:
        iframe_url = extract_youtube_url(
            course_class.pk,
            course_class.video + course_class.other_materials)
        if iframe_url is None:
            continue

        result = urlparse(iframe_url)
        _prefix, yt_id = posixpath.split(result.path)
        course_class.video_url = "http://www.youtube.com/watch?v=" + yt_id
        course_class.save()
        count += 1

    print("Populated {0}/{1} classes, yay!"
          .format(count, len(course_classes)), file=sys.stderr)


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0014_populate_slides_url'),
    ]

    operations = [
        migrations.RunPython(forwards),
    ]
