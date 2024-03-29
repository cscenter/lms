# Generated by Django 3.1.7 on 2021-04-13 16:07

import core.db.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_siteconfiguration_instagram_access_token'),
    ]

    operations = [
        migrations.AlterField(
            model_name='branch',
            name='time_zone',
            field=core.db.fields.TimeZoneField(choices=[('Europe/Kiev', 'Europe/Kiev'), ('Europe/Moscow', 'Europe/Moscow'), ('Europe/Minsk', 'Europe/Minsk'), ('Asia/Yekaterinburg', 'Asia/Yekaterinburg'), ('Asia/Novosibirsk', 'Asia/Novosibirsk')], verbose_name='Timezone'),
        ),
        migrations.AlterField(
            model_name='city',
            name='time_zone',
            field=core.db.fields.TimeZoneField(choices=[('Europe/Kiev', 'Europe/Kiev'), ('Europe/Moscow', 'Europe/Moscow'), ('Europe/Minsk', 'Europe/Minsk'), ('Asia/Yekaterinburg', 'Asia/Yekaterinburg'), ('Asia/Novosibirsk', 'Asia/Novosibirsk')], verbose_name='Timezone'),
        ),
    ]
