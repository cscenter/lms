# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import posixpath
import sys
from urlparse import urlparse
from lxml import html

from django.db import models, migrations

from slides import slideshare


def extract_slideshare_url(pk, html_source):
    html_tree = html.fromstring(html_source)
    iframes = html_tree.xpath(
        "//iframe[contains(@src, 'slideshare.net/slideshow/embed_code')]")
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
    """ Supports links from api 2.x. For 1.x fix manually """
    count = 0
    CourseClass = apps.get_model('learning', 'CourseClass')
    course_classes = CourseClass.objects.filter(
        other_materials__contains="slideshare")
    api = slideshare.get_api()
    for course_class in course_classes:
        iframe_url = extract_slideshare_url(
            course_class.pk, course_class.other_materials)
        if iframe_url is None:
            continue
        result = urlparse(iframe_url)
        _prefix, sl_id = posixpath.split(result.path)
        try:
            sl_meta = api.get_slideshow(sl_id)
            course_class.slides_url = sl_meta["Slideshow"]["URL"]
        except Exception as e:  # Impossible?
            print("{:03d}: unexpected error".format(course_class.pk),
                  file=sys.stderr)
            print(e, file=sys.stderr)
        else:
            html_tree = html.fromstring(course_class.other_materials)
            iframe_count = len(html_tree.xpath("//iframe"))
            if iframe_count == 1:
                course_class.other_materials = ""
            else:
                print("{:03d} PLEASE FIX other_materials MANUALLY!"
                      .format(course_class.pk), file=sys.stderr)

            course_class.save()
            count += 1

    print("Populated {0}/{1} classes, yay!"
          .format(count, len(course_classes)), file=sys.stderr)


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0013_auto_20150908_1840'),
    ]

    operations = [
        migrations.RunPython(forwards),
    ]
