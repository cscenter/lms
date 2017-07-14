from rest_pandas import PandasSerializer
from django.utils.translation import ugettext_lazy as _

from users.models import CSCUser


class ApplicantsResultsSerializer(PandasSerializer):
    def transform_dataframe(self, dataframe):
        return (dataframe
                .pivot_table(index='campaign__year', columns='status',
                             values='total', fill_value=0)
                .reset_index('campaign__year'))


class TestingScoreByUniversitiesSerializer(PandasSerializer):
    def transform_dataframe(self, dataframe):
        return (dataframe
                .pivot_table(index='score',
                             columns='applicant__university__name',
                             values='total',
                             fill_value=0)
                .reset_index('score'))


class TestingScoreByCoursesSerializer(PandasSerializer):
    def transform_dataframe(self, dataframe):
        df = (dataframe
              .pivot_table(index='score',
                           columns='applicant__course',
                           values='total',
                           fill_value=0))
        to_rename = {c: self.index_to_name(c) for c in df.columns}
        df.rename(columns=to_rename, inplace=True)
        df = df.reset_index('score')
        return df

    def index_to_name(self, course_index):
        if course_index in CSCUser.COURSES:
            return str(CSCUser.COURSES[course_index])
        else:
            return str(_("Other"))
