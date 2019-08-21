# Generated by Django 2.2.4 on 2019-08-21 15:01

import core.timezone.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_auto_20190821_1459'),
        ('learning', '0029_auto_20190814_1514'),
    ]

    operations = [
        migrations.CreateModel(
            name='LearningSpace',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, help_text='Leave blank to fill in with location name value', max_length=140, verbose_name='Name')),
                ('description', models.TextField(help_text='How to style text read <a href="/commenting-the-right-way/" target="_blank">here</a>. Partially HTML is enabled too.', verbose_name='Description')),
                ('order', models.PositiveIntegerField(default=100, verbose_name='Order')),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='learning_spaces', to='core.Branch', verbose_name='Branch')),
                ('location', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='learning_spaces', to='core.Location', verbose_name='Location')),
            ],
            options={
                'verbose_name': 'Learning Space',
                'verbose_name_plural': 'Learning Spaces',
            },
            bases=(core.timezone.models.TimezoneAwareModel, models.Model),
        ),
    ]
