# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import logging
import os
import random

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from testfixtures import LogCapture

from django.conf import settings
from django.conf.urls.static import static
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse, NoReverseMatch, RegexURLPattern
from django.db import connection
from django.forms.models import model_to_dict
from django.test.utils import override_settings
from django.test import TestCase
from django.utils.encoding import smart_text

import cscenter.urls
from learning.utils import get_current_term_pair
from learning.models import StudentAssignment
from ..factories import *
from .mixins import *


random.seed(42)


@override_settings(DEBUG=True)
class SmokeTests(MyUtilitiesMixin, TestCase):
    def _populate(self):
        teachers = UserFactory.create_batch(30, groups=['Teacher [CENTER]'])
        students = UserFactory.create_batch(30, groups=['Student [CENTER]'])
        courses = CourseFactory.create_batch(30)
        venues = VenueFactory.create_batch(5)
        semesters = [
            SemesterFactory.create(year=year, type=type_)
            for type_ in ['spring', 'autumn']
            for year in range(2010, 2025)]

        course_offerings = [
            CourseOfferingFactory.create(
                course=random.choice(courses),
                semester=random.choice(semesters),
                teachers=random.sample(teachers, 3))
            for _ in range(100)]

        course_classes = []
        course_offering_news = []
        assignments = []
        for course_offering in course_offerings:
            num_classes = random.randint(5, 15)
            num_news = random.randint(5, 15)
            num_assignments = random.randint(5, 15)
            [course_classes.append(
                CourseClassFactory.create(
                    course_offering=course_offering,
                    venue=random.choice(venues),
                    type=random.choice(['lecture', 'seminar'])))
             for _ in range(num_classes)]
            [course_offering_news.append(
                CourseOfferingNewsFactory.create(
                    course_offering=course_offering))
             for _ in range(num_news)]
            [assignments.append(
                AssignmentFactory.create(
                    course_offering=course_offering))
             for _ in range(num_assignments)]

        enrollments = []
        assignment_comments = []
        for student in students:
            course_offering_sample = random.sample(course_offerings,
                                                   random.randint(0, 10))
            for course_offering in course_offering_sample:
                enrollments.append(EnrollmentFactory.create(
                    student=student,
                    course_offering=course_offering))
            for course_offering in course_offering_sample:
                a_ss = StudentAssignment.objects.filter(
                    assignment__course_offering=course_offering,
                    student=student)
                for a_s in a_ss:
                    num_student_comments = random.randint(0, 5)
                    num_teacher_comments = random.randint(0, 3)
                    for _ in range(num_student_comments):
                        assignment_comments.append(
                            AssignmentCommentFactory.create(
                                student_assignment=a_s,
                                author=student))
                    for _ in range(num_teacher_comments):
                        teacher = random.choice(course_offering.teachers.all())
                        assignment_comments.append(
                            AssignmentCommentFactory.create(
                                student_assignment=a_s,
                                author=teacher))

    def test_num_queries(self):
        return  # too slow, makes life hard
        self._populate()
        for urlpat in cscenter.urls.urlpatterns:
            # FIXME(Dmitry): don't skip nested pathes
            if type(urlpat) != RegexURLPattern:
                continue
            try:
                url = reverse(urlpat.name)
                self.client.get(url)
                num_queries = len(connection.queries)
                # print urlpat.name, num_queries
                if num_queries > 10:
                    self.fail("url {} made too many DB requests ({})"
                              .format(urlpat.name, num_queries))
            except NoReverseMatch:
                # FIXME(Dmitry): don't skip pathes with arguments
                continue
