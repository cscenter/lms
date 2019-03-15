from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from django.db.models import query, Prefetch
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel

from core.models import City
from learning.models import Branch


class AcademicDiscipline(models.Model):
    code = models.CharField(_("PK|Code"), max_length=2, primary_key=True)
    name = models.CharField(_("AreaOfStudy|Name"), max_length=255)
    description = models.TextField(_("AreaOfStudy|description"))

    class Meta:
        db_table = "areas_of_study"
        ordering = ["name"]
        verbose_name = _("Area of study")
        verbose_name_plural = _("Areas of study")

    def __str__(self):
        return smart_text(self.name)


class StudyProgramQuerySet(query.QuerySet):
    def available_core_courses(self):
        """
        Note that not all core courses are mandatory - student must complete
        only one in each group.
        """
        from study_programs.models import StudyProgramCourseGroup
        return (self.select_related("area")
                    .prefetch_related(
                        Prefetch(
                            'course_groups',
                            queryset=(StudyProgramCourseGroup
                                      .objects
                                      .prefetch_related("courses")),
                        )))


class StudyProgram(TimeStampedModel):
    year = models.PositiveSmallIntegerField(
        _("Year"), validators=[MinValueValidator(1990)])
    city = models.ForeignKey(City,
                             verbose_name=_("City"),
                             default=settings.DEFAULT_CITY_CODE,
                             on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch,
                               verbose_name=_("Branch"),
                               related_name="study_programs",
                               on_delete=models.CASCADE)
    area = models.ForeignKey(AcademicDiscipline, verbose_name=_("Area of Study"),
                             on_delete=models.CASCADE)
    description = models.TextField(
        _("StudyProgram|description"),
        blank=True, null=True)

    class Meta:
        db_table = "study_programs"
        verbose_name = _("Study Program")
        verbose_name_plural = _("Study Programs")

    objects = StudyProgramQuerySet.as_manager()


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
