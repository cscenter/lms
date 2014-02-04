# -*- coding: utf-8 -*-

from django.test import TestCase
from django.core.exceptions import ValidationError

from .models import CSCUser

IS_STUDENT_PK = 1
IS_TEACHER_PK = 2
IS_GRADUATE_PK = 3

class UserTests(TestCase):
    def test_student_should_have_enrollment_year(self):
        """
        If user set "student" group (pk=1 in initial_data fixture), they
        should also provide an enrollment year, otherwise they should get
        ValidationError
        """
        user = CSCUser()
        user.save()
        user.groups = [IS_STUDENT_PK]
        self.assertRaises(ValidationError, user.clean)
        user.enrolment_year = 2010
        self.assertIsNone(user.clean())

    def test_graduate_should_have_graduation_year(self):
        """
        If user set "graduate" group (pk=3 in initial_data fixture), they
        should also provide graduation year, otherwise they should get
        ValidationError
        """
        user = CSCUser()
        user.save()
        user.groups = [IS_GRADUATE_PK]
        self.assertRaises(ValidationError, user.clean)
        user.graduation_year = 2011
        self.assertIsNone(user.clean())

    def test_full_name_contains_patronymic(self):
        """
        If "patronymic" is set, get_full_name's result should contain it
        """
        user = CSCUser(first_name=u"Анна", last_name=u"Иванова",
                       patronymic=u"Васильевна")
        self.assertEqual(user.get_full_name(), u"Иванова Анна Васильевна")
        user = CSCUser(first_name=u"Анна", last_name=u"Иванова")
        self.assertEqual(user.get_full_name(), u"Иванова Анна")

    def test_group_props(self):
        """
        Tests properties based on groups (is_student, is_graduate, is_teacher)
        """
        user = CSCUser()
        user.save()
        self.assertFalse(user.is_student)
        self.assertFalse(user.is_teacher)
        self.assertFalse(user.is_graduate)
        user.groups = [IS_STUDENT_PK]
        self.assertTrue(user.is_student)
        self.assertFalse(user.is_teacher)
        self.assertFalse(user.is_graduate)
        user.groups = [IS_STUDENT_PK, IS_TEACHER_PK]
        self.assertTrue(user.is_student)
        self.assertTrue(user.is_teacher)
        self.assertFalse(user.is_graduate)
        user.groups = [IS_STUDENT_PK, IS_TEACHER_PK, IS_GRADUATE_PK]
        self.assertTrue(user.is_student)
        self.assertTrue(user.is_teacher)
        self.assertTrue(user.is_graduate)
