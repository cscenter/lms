# Generated by Django 2.2.4 on 2019-08-13 17:36

import core.mixins
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_auto_20190812_1506'),
    ]

    database_operations = [
    ]

    state_operations = [
        migrations.CreateModel(
            name='Branch',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(choices=[('spb', 'Saint Petersburg'), ('nsk', 'Novosibirsk'), ('distance', 'Branches|Distance')], max_length=8, unique=True, verbose_name='Code')),
                ('name', models.CharField(max_length=255, verbose_name='Branch|Name')),
                ('is_remote', models.BooleanField(default=False, verbose_name='Distance Branch')),
                ('description', models.TextField(blank=True, help_text='Branch|Description', verbose_name='Description')),
            ],
            options={
                'verbose_name': 'Branch',
                'verbose_name_plural': 'Branches',
            },
            bases=(core.mixins.TimezoneAwareModel, models.Model),
        ),
        # migrations.DeleteModel(
        #     name='Branch',
        # ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=database_operations,
            state_operations=state_operations)
    ]