# Generated by Django 3.0.9 on 2020-09-02 08:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_auto_20200514_1750'),
    ]

    operations = [
        migrations.AlterField(
            model_name='branch',
            name='time_zone',
            field=models.CharField(choices=[('Europe/Kiev', 'Europe/Kiev'), ('Europe/Moscow', 'Europe/Moscow'), ('Europe/Minsk', 'Europe/Minsk'), ('Asia/Yekaterinburg', 'Asia/Yekaterinburg'), ('Asia/Novosibirsk', 'Asia/Novosibirsk')], max_length=63, verbose_name='Timezone'),
        ),
        migrations.AlterField(
            model_name='city',
            name='time_zone',
            field=models.CharField(choices=[('Europe/Kiev', 'Europe/Kiev'), ('Europe/Moscow', 'Europe/Moscow'), ('Europe/Minsk', 'Europe/Minsk'), ('Asia/Yekaterinburg', 'Asia/Yekaterinburg'), ('Asia/Novosibirsk', 'Asia/Novosibirsk')], max_length=63, verbose_name='Timezone'),
        ),
    ]
