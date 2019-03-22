from rest_pandas import PandasSerializer
from django.utils.translation import ugettext_lazy as _

from learning.settings import AcademicDegreeYears
from users.models import User


def _index_to_name(course_index):
    return AcademicDegreeYears.values.get(course_index, str(_("Other")))


class CampaignResultsTimelineSerializer(PandasSerializer):
    def transform_dataframe(self, dataframe):
        return (dataframe
                .pivot_table(index='campaign__year', columns='status',
                             values='total', fill_value=0)
                .reset_index('campaign__year'))


class ApplicationFormSubmissionTimelineSerializer(PandasSerializer):
    pass


class CampaignResultsByUniversitiesSerializer(PandasSerializer):
    def transform_dataframe(self, dataframe):
        return (dataframe
                .pivot_table(index='university__name',
                             columns='status',
                             values='total',
                             fill_value=0)
                .reset_index('university__name'))


class CampaignResultsByCoursesSerializer(PandasSerializer):
    def transform_dataframe(self, dataframe):
        df = (dataframe
              .pivot_table(index='course',
                           columns='status',
                           values='total',
                           fill_value=0))
        df.index = df.index.map(_index_to_name)
        df.index.rename("course__name", inplace=True)
        df = df.reset_index('course__name')
        return df


class ScoreByUniversitiesSerializer(PandasSerializer):
    """Both applicable for testing and examination scores serialization"""
    def transform_dataframe(self, dataframe):
        return (dataframe
                .pivot_table(index='score',
                             columns='applicant__university__name',
                             values='total',
                             fill_value=0)
                .reset_index('score'))


class ScoreByCoursesSerializer(PandasSerializer):
    """Both applicable for testing and examination scores serialization"""
    def transform_dataframe(self, dataframe):
        df = (dataframe
              .pivot_table(index='score',
                           columns='applicant__course',
                           values='total',
                           fill_value=0))
        to_rename = {c: _index_to_name(c) for c in df.columns}
        df.rename(columns=to_rename, inplace=True)
        df = df.reset_index('score')
        return df


class ApplicationSubmissionPandasSerializer(PandasSerializer):
    def transform_dataframe(self, dataframe):
        dataframe.date = dataframe.date.apply(lambda d: d.strftime("%d.%m.%Y"))
        dataframe.set_index('date', inplace=True)
        return dataframe

