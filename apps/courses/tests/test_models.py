import pytest
from django.core.exceptions import ValidationError

from core.models import Branch
from core.tests.utils import CSCTestCase

from courses.tests.factories import CourseNewsFactory, SemesterFactory, CourseFactory, \
    CourseClassFactory, CourseClassAttachmentFactory, MetaCourseFactory, \
    AssignmentFactory, AssignmentAttachmentFactory
from courses.models import Semester, Course, Assignment
from courses.constants import SemesterTypes
from courses.utils import get_term_index, next_term_starts_at
from learning.settings import Branches


@pytest.mark.django_db
def test_news_get_timezone(settings):
    news = CourseNewsFactory(course__branch__code=Branches.NSK)
    assert news.get_timezone() == Branches.get_timezone(Branches.NSK)
    news.course.branch = Branch.objects.get(code=Branches.SPB,
                                            site_id=settings.SITE_ID)
    news.course.save()
    news.refresh_from_db()
    assert news.get_timezone() == Branches.get_timezone(Branches.SPB)


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


def test_semester_cmp():
    index = get_term_index(2013, 'spring')
    s2013_spring = Semester(type='spring', year=2013, index=index)
    index = get_term_index(2013, 'autumn')
    s2013_autumn = Semester(type='autumn', year=2013, index=index)
    index = get_term_index(2013, 'summer')
    s2013_summer = Semester(type='summer', year=2013, index=index)
    index = get_term_index(2014, 'spring')
    s2014_spring = Semester(type='spring', year=2014, index=index)
    assert s2013_spring < s2013_autumn
    assert s2013_spring < s2013_summer
    assert s2013_summer < s2013_autumn
    assert s2013_summer < s2014_spring


@pytest.mark.django_db
def test_course_derivable_fields():
    co = CourseFactory()
    assert not co.materials_files
    assert not co.materials_slides
    assert not co.videos_count
    cc = CourseClassFactory(course=co, video_url="https://link/to/youtube")
    co.refresh_from_db()
    assert not co.materials_files
    assert not co.materials_slides
    assert co.videos_count
    _ = CourseClassAttachmentFactory(course_class=cc)
    co.refresh_from_db()
    assert co.materials_files


@pytest.mark.django_db
def test_course_completed_at_default_value():
    semester = SemesterFactory(year=2017, type=SemesterTypes.AUTUMN)
    course = CourseFactory.build(semester=semester)
    assert not course.completed_at
    course = CourseFactory.create(semester=semester)
    next_term_dt = next_term_starts_at(semester.index, course.get_timezone())
    assert course.completed_at == next_term_dt.date()


class CourseTests(CSCTestCase):
    def test_in_current_term(self):
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
        self.assertEqual(n_ongoing, 1)
        timezone.now = lambda: (datetime.datetime(some_year, 11, 8, 0, 0, 0)
                                .replace(tzinfo=timezone.utc))
        meta_course = MetaCourseFactory()
        n_ongoing = sum(CourseFactory(meta_course=meta_course,
                                      semester=semester).in_current_term
                        for semester in semesters)
        self.assertEqual(n_ongoing, 1)
        timezone.now = old_now


class CourseClassTests(CSCTestCase):
    def test_start_end_validation(self):
        time1 = "13:00"
        time2 = "14:20"
        cc = CourseClassFactory.create(starts_at=time1, ends_at=time2)
        self.assertEqual(None, cc.clean())
        cc = CourseClassFactory.create(starts_at=time2, ends_at=time1)
        self.assertRaises(ValidationError, cc.clean)

    def test_display_prop(self):
        cc = CourseClassFactory.create(type='lecture')
        self.assertEqual("Lecture", cc.get_type_display())


class AssignmentTest(CSCTestCase):
    def test_clean(self):
        co1 = CourseFactory.create()
        co2 = CourseFactory.create()
        a = AssignmentFactory.create(course=co1)
        a_copy = Assignment.objects.filter(pk=a.pk).get()
        a_copy.course = co2
        self.assertRaises(ValidationError, a_copy.clean)
        a_copy.course = co1
        a_copy.save()
        a_copy.passing_score = a.maximum_score + 1
        self.assertRaises(ValidationError, a_copy.clean)

    def test_is_open(self):
        import datetime
        from django.utils import timezone
        a = AssignmentFactory()
        self.assertTrue(a.is_open)
        a.deadline_at = timezone.now() - datetime.timedelta(days=2)
        self.assertFalse(a.is_open)


class AssignmentAttachmentTest(CSCTestCase):
    def test_attached_file_name(self):
        fname = "foobar.pdf"
        aa = AssignmentAttachmentFactory.create(attachment__filename=fname)
        self.assertRegex(aa.file_name, "^foobar(_[0-9a-zA-Z]+)?.pdf$")