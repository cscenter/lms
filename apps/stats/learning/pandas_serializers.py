from rest_pandas import PandasSerializer


class StudentsByTypePandasSerializer(PandasSerializer):
    def transform_dataframe(self, dataframe):
        """Counts how many students of each type participate in the course"""
        return dataframe.value_counts('type').to_frame(name='count')


class ParticipantsByYearPandasSerializer(PandasSerializer):
    def transform_dataframe(self, dataframe):
        df = (dataframe
              .groupby("curriculum_year", as_index=False)
              .agg({"groups": "count"}))
        df.rename(columns={"groups": "students"}, inplace=True)
        return df

