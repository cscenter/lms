# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import re
import sys

from lxml import html
from micawber.contrib.mcdjango import extract_oembed

from django.db import models, migrations


def bruteforce_yandex_embeds():
    return {}
    embeds = {}
    for idx in range(1, 512):
        url = ("https://video.yandex.ru/users/csc-video/view/{}"
               .format(idx))
        response = extract_oembed(url)
        if not response:
            continue
        else:
            [(_url, meta)] = response
            iframe_url = extract_yandex_url(-1, meta["html"])
            embeds[iframe_url] = url
    return embeds


def extract_yandex_url(pk, html_source):
    html_tree = html.fromstring(html_source)
    iframes = html_tree.xpath(
        "//iframe[contains(@src, 'video.yandex.ru/iframe/csc-video')]")
    if not iframes:
        print("{:03d} no embed found".format(pk), file=sys.stderr)
        print(html_source, file=sys.stderr)
        return
    elif len(iframes) > 1:
        print("{:03d}: multiple embeds found".format(pk), file=sys.stderr)
        print(html_source, file=sys.stderr)
        return

    [iframe] = iframes
    return re.sub("https?:", "", iframe.attrib["src"].rstrip("/"))


def forwards(apps, schema_editor):
    count = 0
    CourseClass = apps.get_model('learning', 'CourseClass')
    print("Populating embed->URL map via bruteforce ...", end=" ",
          file=sys.stderr)
    embeds = bruteforce_yandex_embeds()
    print("resolved {} embeds".format(len(embeds)), file=sys.stderr)

    count = 0
    q = (models.Q(video__contains="yandex") |
         models.Q(other_materials__contains="yandex"))
    course_classes = CourseClass.objects.filter(q)
    for course_class in course_classes:
        iframe_url = extract_yandex_url(
            course_class.pk,
            course_class.video + course_class.other_materials)
        if iframe_url is None:
            continue
        elif iframe_url not in embeds:
            print("Failed to lookup {} in embed->URL map"
                  .format(iframe_url), file=sys.stderr)
            continue

        course_class.video_url = embeds[iframe_url]
        course_class.save()
        count += 1

    print("Populated {0}/{1} classes, yay!"
          .format(count, len(course_classes)), file=sys.stderr)



class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0015_populate_video_url_youtube'),
    ]

    operations = [
        migrations.RunPython(forwards),
    ]
