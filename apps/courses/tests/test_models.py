import re

import pytest
from django.core.exceptions import ValidationError

from core.models import Branch
from core.tests.factories import BranchFactory
from courses.constants import SemesterTypes
from courses.models import Assignment
from courses.tests.factories import CourseNewsFactory, SemesterFactory, \
    CourseFactory, \
    CourseClassFactory, CourseClassAttachmentFactory, MetaCourseFactory, \
    AssignmentFactory, AssignmentAttachmentFactory
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
    co = CourseFactory()
    assert not co.public_attachments_count
    assert not co.public_slides_count
    assert not co.public_videos_count
    cc = CourseClassFactory(course=co, video_url="https://link/to/youtube")
    co.refresh_from_db()
    assert not co.public_attachments_count
    assert not co.public_slides_count
    assert co.public_videos_count
    _ = CourseClassAttachmentFactory(course_class=cc)
    co.refresh_from_db()
    assert co.public_attachments_count


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
    branch_spb_center = BranchFactory(site__domain=settings.TEST_DOMAIN)
    branch_spb_club = BranchFactory(site__domain=settings.ANOTHER_DOMAIN)
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
def test_assignment_is_open():
    import datetime
    from django.utils import timezone
    a = AssignmentFactory()
    assert a.is_open
    a.deadline_at = timezone.now() - datetime.timedelta(days=2)
    assert not a.is_open


@pytest.mark.django_db
def test_assignment_attached_file_name():
    fname = "foobar.pdf"
    aa = AssignmentAttachmentFactory.create(attachment__filename=fname)
    assert re.match("^foobar(_[0-9a-zA-Z]+)?.pdf$", aa.file_name)
