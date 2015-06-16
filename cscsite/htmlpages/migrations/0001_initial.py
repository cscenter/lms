# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def forwards_func(apps, schema_editor):
    htmlpages = apps.get_model('flatpages', 'flatpage')
    db_alias = schema_editor.connection.alias
    initial_pages = [
                    {
                        "url": "/syllabus/",
                        "title": "Syllabus",
                        "content": "# Syllabus\n\nThis is Computer Science Center syllabus. **Please change this content**.",
                    },
                    {
                        "url": "/application/",
                        "title": "Application",
                        "content": "# Application\n\nThis is Computer Science Center application. **Please change this content**.",
                    },
                    {
                        "url": "/orgs/",
                        "title": "Organizers",
                        "content": "# Organizers\n\nThis is a list of people that made Computer Science Center real. **Please change this content**."
                    },
                    {
                        "url": "/contacts/",
                        "title": "Contacts",
                        "content": "# Contacts\r\n\r\nThis is how you can contact Computer Science Center. **Please change this content**.\r\n\r\n[CSCenter learning venues](/venues)"
                    },
                    {
                        "url": "/enrollment/",
                        "title": "Enrollment",
                        "content": "# Enrollment\n\nThis is how you can enroll at Computer Science Center. **Please change this content**."
                    },
                    {
                        "url": "/learning/useful/",
                        "title": "Useful stuff",
                        "content": "# Licenses\n\nThis is a list of licenses available for Computer Science Center students. **Please change this content**."
                    },
                    {
                        "url": "/online/",
                        "title": "Online",
                        "content": "# Online\n\nThis is \"online\" page. **Please change this content**."
                    },
                    {
                        "url": "/lectures/",
                        "title": "Lectures",
                        "content": "# Lectures\n\nThis is \"lectures\" page. **Please change this content**."
                    }
                    ]
    compscicenter_id = 1
    for page in initial_pages:
        htmlpage = htmlpages(**page)
        htmlpage.save(force_insert=True, using=db_alias)
        htmlpage.sites.add(compscicenter_id)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(forwards_func),
    ]
