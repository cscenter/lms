from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction

from django.db.models import query, Prefetch
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from sorl.thumbnail import ImageField

from core.models import City
from courses.models import MetaCourse
from learning.models import Branch


class AcademicDiscipline(models.Model):
    code = models.CharField(_("PK|Code"), max_length=2, primary_key=True)
    name = models.CharField(_("AreaOfStudy|Name"), max_length=255)
    cover = ImageField(
        _("AcademicDiscipline|cover"),
        upload_to="academic_disciplines/",
        blank=True)
    icon = models.FileField(
        _("AcademicDiscipline|icon"),
        upload_to="academic_disciplines/",
        blank=True)
    description = models.TextField(_("AreaOfStudy|description"))

    class Meta:
        db_table = "areas_of_study"
        ordering = ["name"]
        verbose_name = _("Area of study")
        verbose_name_plural = _("Areas of study")

    def __str__(self):
        return smart_text(self.name)


class StudyProgramQuerySet(query.QuerySet):
    def prefetch_core_courses_groups(self):
        """
        Note that not all core courses are mandatory - student must complete
        only one in each group.
        """
        from study_programs.models import StudyProgramCourseGroup
        return self.prefetch_related(
            Prefetch(
                'course_groups',
                queryset=(StudyProgramCourseGroup.objects
                          .prefetch_related("courses"))))


class StudyProgram(TimeStampedModel):
    year = models.PositiveSmallIntegerField(
        _("Year"), validators=[MinValueValidator(1990)])
    city = models.ForeignKey(City,
                             verbose_name=_("City"),
                             default=settings.DEFAULT_CITY_CODE,
                             on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch,
                               verbose_name=_("Branch"),
                               to_field="code",
                               related_name="study_programs",
                               on_delete=models.CASCADE)
    academic_discipline = models.ForeignKey(
        AcademicDiscipline,
        verbose_name=_("Area of Study"),
        related_query_name="study_program",
        on_delete=models.CASCADE)
    is_active = models.BooleanField(
        _("Activity"),
        help_text=_("Show on syllabus page. Other activity flags for selected "
                    "city and academic discipline will be deactivated."),
        default=True)
    description = models.TextField(
        _("StudyProgram|description"),
        blank=True, null=True)

    class Meta:
        db_table = "study_programs"
        verbose_name = _("Study Program")
        verbose_name_plural = _("Study Programs")

    objects = StudyProgramQuerySet.as_manager()

    @transaction.atomic
    def save(self, **kwargs):
        created = self.pk is None
        super().save(**kwargs)
        if self.is_active:
            # Deactivate other records with the same academic
            # discipline and city
            (StudyProgram.objects
             .filter(is_active=True,
                     academic_discipline_id=self.academic_discipline_id,
                     branch=self.branch)
             .exclude(pk=self.pk)
             .update(is_active=False))

    def get_courses(self):
        """Returns all core courses sorted by name"""
        return (MetaCourse.objects
                .filter(studyprogramcoursegroup__in=self.course_groups.all())
                .defer("description", "created", "modified"))


class StudyProgramCourseGroup(models.Model):
    courses = models.ManyToManyField(
        'courses.MetaCourse',
        verbose_name=_("StudyProgramCourseGroup|courses"),
        help_text=_("Courses will be grouped with boolean OR"))
    study_program = models.ForeignKey(
        'StudyProgram',
        verbose_name=_("Study Program"),
        related_name='course_groups',
        on_delete=models.PROTECT)

    class Meta:
        db_table = "study_programs_groups"
        verbose_name = _("Study Program Course")
        verbose_name_plural = _("Study Program Courses")
