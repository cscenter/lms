from itertools import chain

import pandas as pd
from rest_pandas import PandasSerializer


class ParticipantsByGroupPandasSerializer(PandasSerializer):
    def transform_dataframe(self, dataframe):
        df = (pd.DataFrame((x for x in chain.from_iterable(dataframe.groups)),
                           columns=['group_id'])
              .group_id
              .value_counts(sort=False)
              .to_frame(name="students"))
        df.index.set_names('group', inplace=True)
        df.reset_index(inplace=True)
        return df


class ParticipantsByYearPandasSerializer(PandasSerializer):
    def transform_dataframe(self, dataframe):
        df = (dataframe
              .groupby("curriculum_year", as_index=False)
              .agg({"groups": "count"}))
        df.rename(columns={"groups": "students"}, inplace=True)
        return df

