# Generated by Django 2.2.4 on 2019-08-21 15:36

from django.db import migrations


def fix_tz(apps, schema_editor):
    City = apps.get_model('core', 'City')
    for c in City.objects.all():
        if c.code == 'nsk':
            c.time_zone = 'Asia/Novosibirsk'
            c.save(update_fields=('time_zone',))

    Location = apps.get_model('core', 'Location')
    for c in Location.objects.all():
        if c.city_id == 'nsk':
            c.time_zone = 'Asia/Novosibirsk'
            c.save(update_fields=('time_zone',))


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_city_time_zone'),
    ]

    operations = [
        migrations.RunPython(fix_tz)
    ]
