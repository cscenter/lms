from rest_pandas import PandasSerializer


class ApplicantsResultsSerializer(PandasSerializer):
    def transform_dataframe(self, dataframe):
        return (dataframe
                .pivot_table(index='campaign__year', columns='status',
                             values='total', fill_value=0)
                .reset_index('campaign__year'))
