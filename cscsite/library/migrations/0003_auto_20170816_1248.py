# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-08-16 12:48
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_1(apps, schema_editor):
    Book = apps.get_model('library', 'Book')
    Stock = apps.get_model('library', 'Stock')
    # First, copy from book to stock
    for book in Book.objects.all():
        stock = Stock(copies=book.copies, book_id=book.pk, city_id='spb')
        stock.save()


def migrate_2(apps, schema_editor):
    Book = apps.get_model('library', 'Book')
    Borrow = apps.get_model('library', 'Borrow')
    Stock = apps.get_model('library', 'Stock')
    # First, copy from book to stock
    for stock in Stock.objects.all():
        for borrow in Borrow.objects.filter(book_id=stock.book_id):
            borrow.stock_id = stock.pk
            borrow.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('library', '0002_auto_20160122_1855'),
    ]

    operations = [
        migrations.CreateModel(
            name='Stock',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('copies', models.PositiveSmallIntegerField(default=1, verbose_name='Book|number of copies')),
            ],
            options={
                'verbose_name': 'Stock',
                'verbose_name_plural': 'Stocks',
            },
        ),
        migrations.AlterField(
            model_name='book',
            name='read_by',
            field=models.ManyToManyField(related_name='books_legacy', through='library.Borrow', to=settings.AUTH_USER_MODEL, verbose_name='read by'),
        ),
        migrations.AddField(
            model_name='stock',
            name='book',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='library.Book', verbose_name='Book'),
        ),
        migrations.AddField(
            model_name='stock',
            name='city',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.City', verbose_name='City'),
        ),
        migrations.AddField(
            model_name='stock',
            name='read_by',
            field=models.ManyToManyField(related_name='books', through='library.Borrow', to=settings.AUTH_USER_MODEL, verbose_name='read by'),
        ),
        migrations.RunPython(migrate_1),
        migrations.AddField(
            model_name='borrow',
            name='stock',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='library.Stock'),
            preserve_default=False,
        ),
        migrations.RunPython(migrate_2),
    ]
