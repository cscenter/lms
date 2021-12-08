import datetime
import re

import pytest
import pytz

from django.core.exceptions import ValidationError
from django.db.models import Prefetch

from core.models import Branch
from core.tests.factories import BranchFactory
from core.tests.settings import ANOTHER_DOMAIN, TEST_DOMAIN
from courses.constants import MaterialVisibilityTypes, SemesterTypes
from courses.models import Assignment, Course, CourseClass, CourseTeacher
from courses.selectors import course_teachers_prefetch_queryset
from courses.tests.factories import (
    AssignmentAttachmentFactory, AssignmentFactory, CourseClassAttachmentFactory,
    CourseClassFactory, CourseFactory, CourseNewsFactory, CourseTeacherFactory,
    MetaCourseFactory, SemesterFactory
)
from courses.utils import TermPair
from learning.settings import Branches


@pytest.mark.django_db
def test_news_get_timezone(settings):
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    news = CourseNewsFactory(course__main_branch__code=Branches.NSK)
    assert news.get_timezone() == branch_nsk.get_timezone()
    news.course.main_branch = Branch.objects.get(code=Branches.SPB,
                                                 site_id=settings.SITE_ID)
    news.course.save()
    news.refresh_from_db()
    assert news.get_timezone() == branch_spb.get_timezone()


@pytest.mark.django_db
def test_course_teacher_get_most_priority_role_prefetch(django_assert_num_queries):
    """Make sure teachers are ordered by the most priority role"""
    course = CourseFactory()
    ct1, ct2, ct3, ct4 = CourseTeacherFactory.create_batch(4, course=course)
    ct1.roles = CourseTeacher.roles.seminar
    ct1.save()
    ct2.roles = CourseTeacher.roles.lecturer | CourseTeacher.roles.seminar
    ct2.save()
    ct3.roles = CourseTeacher.roles.reviewer
    ct3.save()
    ct4.roles = CourseTeacher.roles.lecturer
    ct4.save()
    course_teachers = Prefetch('course_teachers',
                               queryset=course_teachers_prefetch_queryset())
    with django_assert_num_queries(2):
        course = (Course.objects
                  .filter(pk=course.pk)
                  .prefetch_related(course_teachers)
                  .get())
        prefetched = [ct.pk for ct in course.course_teachers.all()]
        assert prefetched == [ct2.pk, ct4.pk, ct1.pk, ct3.pk]
        assert course.course_teachers.all()[0].get_abbreviated_name() == ct2.teacher.get_abbreviated_name()


@pytest.mark.django_db
def test_course_teacher_has_any_hidden_role():
    course = CourseFactory()
    course_teacher = CourseTeacherFactory(course=course, roles=CourseTeacher.roles.reviewer)
    assert CourseTeacher.objects.filter(CourseTeacher.has_any_hidden_role()).count() == 0
    CourseTeacherFactory(course=course, roles=CourseTeacher.roles.reviewer | CourseTeacher.roles.spectator)
    assert CourseTeacher.objects.filter(CourseTeacher.has_any_hidden_role()).count() == 1
    CourseTeacherFactory(course=course, roles=CourseTeacher.roles.organizer | CourseTeacher.roles.spectator)
    assert CourseTeacher.objects.filter(CourseTeacher.has_any_hidden_role()).count() == 2
    CourseTeacherFactory(course=course, roles=CourseTeacher.roles.organizer)
    assert CourseTeacher.objects.filter(CourseTeacher.has_any_hidden_role()).count() == 3
    assert CourseTeacher.objects.exclude(CourseTeacher.has_any_hidden_role()).count() == 1
    assert CourseTeacher.objects.exclude(CourseTeacher.has_any_hidden_role()).get() == course_teacher
    CourseTeacherFactory(course=course, roles=CourseTeacher.roles.reviewer | CourseTeacher.roles.lecturer)
    assert CourseTeacher.objects.exclude(CourseTeacher.has_any_hidden_role()).count() == 2


@pytest.mark.django_db
def test_semester_starts_ends():
    import datetime

    from django.utils import timezone
    spring_2015_date = (datetime.datetime(2015, 4, 8, 0, 0, 0)
                        .replace(tzinfo=timezone.utc))
    # Summer term starts from 1 jul
    summer_2015_date = (datetime.datetime(2015, 7, 8, 0, 0, 0)
                        .replace(tzinfo=timezone.utc))
    autumn_2015_date = (datetime.datetime(2015, 11, 8, 0, 0, 0)
                        .replace(tzinfo=timezone.utc))
    spring_2016_date = (datetime.datetime(2016, 4, 8, 0, 0, 0)
                        .replace(tzinfo=timezone.utc))
    spring_2015 = SemesterFactory(type='spring', year=2015)
    summer_2015 = SemesterFactory(type='summer', year=2015)
    autumn_2015 = SemesterFactory(type='autumn', year=2015)
    spring_2016 = SemesterFactory(type='spring', year=2016)
    # Check starts < ends
    assert spring_2015.starts_at < spring_2015.ends_at
    assert summer_2015.starts_at < summer_2015.ends_at
    assert autumn_2015.starts_at < autumn_2015.ends_at
    # Check relativity
    assert spring_2015.ends_at < summer_2015.starts_at
    assert summer_2015.ends_at < autumn_2015.starts_at
    assert autumn_2015.ends_at < spring_2016.starts_at
    # Spring date inside spring semester
    assert spring_2015.starts_at < spring_2015_date
    assert spring_2015_date < spring_2015.ends_at
    # And outside others
    assert spring_2015_date < summer_2015.starts_at
    assert spring_2016_date > autumn_2015.ends_at
    # Summer date inside summer term
    assert summer_2015_date > summer_2015.starts_at
    assert summer_2015_date < summer_2015.ends_at
    # Autumn date inside autumn term
    assert autumn_2015_date > autumn_2015.starts_at
    assert autumn_2015_date < autumn_2015.ends_at


@pytest.mark.django_db
def test_semester_cmp():
    s2013_autumn = SemesterFactory(type=SemesterTypes.AUTUMN, year=2013)
    s2013_spring = SemesterFactory(type=SemesterTypes.SPRING, year=2013)
    s2013_summer = SemesterFactory(type=SemesterTypes.SUMMER, year=2013)
    s2014_spring = SemesterFactory(type=SemesterTypes.SPRING, year=2014)
    assert s2013_spring < s2013_autumn
    assert s2013_spring < s2013_summer
    assert s2013_summer < s2013_autumn
    assert s2013_summer < s2014_spring


@pytest.mark.django_db
def test_course_derivable_fields():
    co = CourseFactory(materials_visibility=MaterialVisibilityTypes.PUBLIC)
    assert not co.public_attachments_count
    assert not co.public_slides_count
    assert not co.public_videos_count
    cc = CourseClassFactory(course=co, video_url="https://link/to/youtube",
                            materials_visibility=MaterialVisibilityTypes.PARTICIPANTS)
    co.refresh_from_db()
    assert not co.public_attachments_count
    assert not co.public_slides_count
    assert not co.public_videos_count
    _ = CourseClassAttachmentFactory(course_class=cc)
    co.refresh_from_db()
    assert not co.public_attachments_count
    cc.materials_visibility = MaterialVisibilityTypes.PUBLIC
    cc.save()
    co.refresh_from_db()
    assert co.public_attachments_count == 1
    assert co.public_videos_count == 1
    assert co.public_slides_count == 0


@pytest.mark.django_db
def test_course_completed_at_default_value():
    semester = SemesterFactory(year=2017, type=SemesterTypes.AUTUMN)
    course = CourseFactory.build(semester=semester)
    assert not course.completed_at
    course = CourseFactory.create(semester=semester)
    next_term = TermPair(semester.year, semester.type).get_next()
    assert course.completed_at == next_term.starts_at(course.get_timezone()).date()


@pytest.mark.django_db
def test_course_is_club_course(settings):
    """
    Center courses should not be considered as Club courses even if they were shared with CS Club
    """
    branch_spb_center = BranchFactory(site__domain=TEST_DOMAIN)
    branch_spb_club = BranchFactory(site__domain=ANOTHER_DOMAIN)
    course_center = CourseFactory(main_branch=branch_spb_center)
    course_club = CourseFactory(main_branch=branch_spb_club)
    course_center.branches.add(branch_spb_club)

    assert not course_center.is_club_course
    assert course_club.is_club_course


@pytest.mark.django_db
def test_in_current_term(client):
    """
    In the near future only one course should be "ongoing".
    """
    import datetime

    from django.utils import timezone
    future_year = datetime.datetime.now().year + 20
    some_year = future_year - 5
    semesters = [SemesterFactory(year=year, type=t)
                 for t in ['spring', 'autumn']
                 for year in range(2010, future_year)]
    old_now = timezone.now
    timezone.now = lambda: (datetime.datetime(some_year, 4, 8, 0, 0, 0)
                            .replace(tzinfo=timezone.utc))
    meta_course = MetaCourseFactory()
    n_ongoing = sum(CourseFactory(meta_course=meta_course,
                                  semester=semester).in_current_term
                    for semester in semesters)
    assert n_ongoing == 1
    timezone.now = lambda: (datetime.datetime(some_year, 11, 8, 0, 0, 0)
                            .replace(tzinfo=timezone.utc))
    meta_course = MetaCourseFactory()
    n_ongoing = sum(CourseFactory(meta_course=meta_course,
                                  semester=semester).in_current_term
                    for semester in semesters)
    assert n_ongoing == 1
    timezone.now = old_now


@pytest.mark.django_db
def test_course_class_start_end_validation():
    time1 = "13:00"
    time2 = "14:20"
    cc = CourseClassFactory.create(starts_at=time1, ends_at=time2)
    assert cc.clean() is None
    cc = CourseClassFactory.create(starts_at=time2, ends_at=time1)
    with pytest.raises(ValidationError):
        cc.clean()


def test_course_class_starts_at_local():
    course_class = CourseClass(date=datetime.date(year=2020, month=1, day=1),
                               starts_at=datetime.time(hour=23, minute=20),
                               ends_at=datetime.time(hour=2, minute=20),
                               time_zone=pytz.timezone('Europe/Moscow'))
    assert course_class.starts_at_local().strftime('%H:%M') == '23:20'
    assert course_class.starts_at_local(pytz.UTC).strftime('%H:%M') == '20:20'
    assert course_class.starts_at_local(pytz.timezone('Asia/Novosibirsk')).strftime('%d %H:%M') == '02 03:20'
    # Ambiguous dates will be resolved with is_dst=False
    eastern = pytz.timezone('US/Eastern')
    ambiguous = datetime.datetime(year=2002, month=10, day=27, hour=1, minute=30)
    course_class = CourseClass(date=ambiguous.date(),
                               starts_at=ambiguous.time(),
                               ends_at=datetime.time(hour=5, minute=0),
                               time_zone=eastern)
    assert course_class.starts_at_local() == eastern.localize(ambiguous, is_dst=False)


def test_course_class_ends_at_local():
    course_class = CourseClass(date=datetime.date(year=2020, month=1, day=1),
                               starts_at=datetime.time(hour=21, minute=20),
                               ends_at=datetime.time(hour=23, minute=20),
                               time_zone=pytz.timezone('Europe/Moscow'))
    assert course_class.ends_at_local().strftime('%H:%M') == '23:20'
    assert course_class.ends_at_local(pytz.UTC).strftime('%H:%M') == '20:20'
    assert course_class.ends_at_local(pytz.timezone('Asia/Novosibirsk')).strftime('%d %H:%M') == '02 03:20'
    # Ambiguous dates will be resolved with is_dst=False
    eastern = pytz.timezone('US/Eastern')
    ambiguous = datetime.datetime(year=2002, month=10, day=27, hour=1, minute=30)
    course_class = CourseClass(date=ambiguous.date(),
                               starts_at=datetime.time(hour=0, minute=10),
                               ends_at=ambiguous.time(),
                               time_zone=eastern)
    assert course_class.ends_at_local() == eastern.localize(ambiguous, is_dst=False)


@pytest.mark.django_db
def test_course_class_display_prop():
    cc = CourseClassFactory.create(type='lecture')
    assert cc.get_type_display() == "Lecture"


@pytest.mark.django_db
def test_assignment_clean():
    co1 = CourseFactory.create()
    co2 = CourseFactory.create()
    a = AssignmentFactory.create(course=co1)
    a_copy = Assignment.objects.filter(pk=a.pk).get()
    a_copy.course = co2
    with pytest.raises(ValidationError):
        a_copy.clean()
    a_copy.course = co1
    a_copy.save()
    a_copy.passing_score = a.maximum_score + 1
    with pytest.raises(ValidationError):
        a_copy.clean()


@pytest.mark.django_db
def test_assignment_is_not_exceeded():
    import datetime

    from django.utils import timezone
    a = AssignmentFactory()
    assert not a.deadline_is_exceeded
    a.deadline_at = timezone.now() - datetime.timedelta(days=2)
    assert a.deadline_is_exceeded


@pytest.mark.django_db
def test_assignment_attached_file_name():
    fname = "foobar.pdf"
    aa = AssignmentAttachmentFactory.create(attachment__filename=fname)
    assert re.match("^foobar(_[0-9a-zA-Z]+)?.pdf$", aa.file_name)


@pytest.mark.parametrize("teacher_role", CourseTeacher.roles.itervalues())
@pytest.mark.django_db
def test_course_is_actual_teacher(teacher_role):
    course = CourseFactory()
    ct = CourseTeacherFactory(course=course, roles=teacher_role)
    is_teacher = course.is_actual_teacher(ct.teacher.pk)
    if teacher_role != CourseTeacher.roles.spectator:
        assert is_teacher
    else:
        assert not is_teacher  # spectator is not actual teacher
