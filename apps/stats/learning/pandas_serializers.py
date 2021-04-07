from rest_pandas import PandasSerializer


class StudentsTotalByTypePandasSerializer(PandasSerializer):
    def transform_dataframe(self, dataframe):
        """Counts how many students of each type participate in the course"""
        return dataframe.value_counts('type', sort=False).to_frame(name='count')


class StudentsTotalByYearPandasSerializer(PandasSerializer):
    def transform_dataframe(self, dataframe):
        return dataframe.value_counts('year_of_admission', sort=False).to_frame(name='count')

