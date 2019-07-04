# Generated by Django 2.2.3 on 2019-07-04 16:02

from django.db import migrations

from users.constants import AcademicRoles


def mutate_groups(apps, schema_editor):
    """
    TEACHER_CLUB -> TEACHER + site = compsciclub.ru
    STUDENT_CLUB -> STUDENT + site = compsciclub.ru
    """
    User = apps.get_model('users', 'User')
    for user in User.objects.all():
        for user_group in user.groups.all():
            # 5 - AcademicRoles.STUDENT_CLUB
            if user_group.role == 5:
                assert user_group.site_id == 2
                user_group.role = AcademicRoles.STUDENT
                user_group.save()
            # 6 - AcademicRoles.TEACHER_CLUB
            elif user_group.role == 6:
                assert user_group.site_id == 2
                user_group.role = AcademicRoles.TEACHER
                user_group.save()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_auto_20190704_1602'),
    ]

    operations = [
        migrations.RunPython(mutate_groups)
    ]
