# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import sorl.thumbnail.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Book',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('author', models.CharField(max_length=255, verbose_name='Book|author')),
                ('title', models.CharField(max_length=255, verbose_name='Book|title')),
                ('description', models.TextField(default='', verbose_name='Book|description')),
                ('cover', sorl.thumbnail.fields.ImageField(upload_to='books', null=True, verbose_name='Book|cover', blank=True)),
                ('copies', models.PositiveSmallIntegerField(default=1, verbose_name='Book|number of copies')),
            ],
            options={
                'ordering': ['title'],
                'verbose_name': 'book',
                'verbose_name_plural': 'books',
            },
        ),
        migrations.CreateModel(
            name='Borrow',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('borrowed_on', models.DateField(verbose_name='Borrow|borrowed on')),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='library.Book')),
            ],
            options={
                'ordering': ['borrowed_on'],
                'verbose_name': 'borrow',
                'verbose_name_plural': 'borrows',
            },
        ),
    ]
