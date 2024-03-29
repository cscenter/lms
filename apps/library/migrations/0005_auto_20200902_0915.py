# Generated by Django 3.0.9 on 2020-09-02 09:15

from django.db import migrations
import sorl.thumbnail.fields


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0004_auto_20200902_0811'),
    ]

    operations = [
        migrations.AlterField(
            model_name='book',
            name='cover',
            field=sorl.thumbnail.fields.ImageField(blank=True, default='', max_length=200, upload_to='books', verbose_name='Book|cover'),
            preserve_default=False,
        ),
    ]
