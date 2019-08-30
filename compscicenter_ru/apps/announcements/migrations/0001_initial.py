# Generated by Django 2.2.4 on 2019-08-30 08:14

import announcements.models
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import taggit.managers


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('name', models.CharField(max_length=255, verbose_name='Title')),
                ('slug', models.SlugField(help_text='Write the URL part after `compscicenter.ru/` If this is an open lecture, add `open-lecture-` prefix', verbose_name='Slug')),
                ('publish_start_at', models.DateTimeField(default=announcements.models.timezone_now, verbose_name='Publish Start at')),
                ('publish_end_at', models.DateTimeField(verbose_name='Publish End at')),
                ('short_description', models.TextField(verbose_name='Short Description')),
                ('description', models.TextField(blank=True, help_text="Don't forget to add &lt;h3&gt;Title&lt;/h3&gt; on the first line", verbose_name='Detail Description')),
                ('thumbnail', models.ImageField(blank=True, help_text='Recommended dimensions 600x400', null=True, upload_to='announcements/', verbose_name='Photo')),
                ('actions', models.TextField(blank=True, default='<a class="btn _big _primary _m-wide" href="">Зарегистрироваться</a>', verbose_name='Actions')),
            ],
            options={
                'verbose_name': 'Announcement',
                'verbose_name_plural': 'Announcements',
            },
        ),
        migrations.CreateModel(
            name='AnnouncementTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Name')),
                ('slug', models.SlugField(max_length=100, unique=True, verbose_name='Slug')),
                ('modifier', models.CharField(blank=True, help_text='This class could affect the tag view', max_length=20, null=True, verbose_name='Modifier')),
            ],
            options={
                'verbose_name': 'Announcement Tag',
                'verbose_name_plural': 'Announcement Tags',
            },
        ),
        migrations.CreateModel(
            name='AnnouncementEventDetails',
            fields=[
                ('announcement', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='event_details', serialize=False, to='announcements.Announcement')),
                ('starts_on', models.DateField(blank=True, null=True, verbose_name='Start Date')),
                ('starts_at', models.TimeField(blank=True, null=True, verbose_name='Start Time')),
                ('ends_on', models.DateField(blank=True, null=True, verbose_name='End Date')),
                ('ends_at', models.TimeField(blank=True, null=True, verbose_name='End Time')),
            ],
            options={
                'verbose_name': 'Announcement Details',
                'verbose_name_plural': 'Announcement Details',
            },
        ),
        migrations.CreateModel(
            name='TaggedAnnouncement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content_object', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='announcements.Announcement')),
                ('tag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='announcements_taggedannouncement_items', to='announcements.AnnouncementTag')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='announcement',
            name='tags',
            field=taggit.managers.TaggableManager(blank=True, help_text='A comma-separated list of tags.', through='announcements.TaggedAnnouncement', to='announcements.AnnouncementTag', verbose_name='Tags'),
        ),
    ]
