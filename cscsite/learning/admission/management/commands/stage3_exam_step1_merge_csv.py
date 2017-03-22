# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import tablib
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = (
        """ 
        Run this file to solve problem with inconsistent data before import 
        exam results.

        XXX: Формат файла с результатами ручной проверки может меняться из года
        в год, надо быть внимательным!
        Проблема следующая: есть задания, которые проверяются вручную
        За эти задания могут поставить произвольный балл от 0 до max
        Но в файле с результатами контеста всегда стоит max балл за задания
        Соответственно, это отражается и на общем балле в основном csv.
        Поэтому перед импортом результатов экзамена нужно:
        1. В доп. файле почистить суммарный балл до int
        2. для каждой строки в основном csv по user_name найти в доп. файле
        все релевантные записи, для каждой найденной записи выцепить
        актуальный балл для указанной задачи (там же столбец есть) и
        обновить суммарный балл (и показатели в столбце с задачей)
        в основном файле на основе полученных  значений.
        """
    )
    ADDITIONAL_CSV_ASSIGNMENT_NAME_COL_INDEX = 2
    ADDITIONAL_CSV_USERNAME_COL_INDEX = 3
    ADDITIONAL_CSV_SCORE_COL_INDEX = 8

    def add_arguments(self, parser):
        parser.add_argument('csv', metavar='CSV',
                   help='path to csv with data')
        parser.add_argument('csv2', metavar='CSV',
                            help='path to csv with additional data')
        parser.add_argument('new', help='path to new file data')

    def search_user(self, username, add_dataset):
        """Search username in additional csv by user_name value"""
        for row in add_dataset:
            if row[self.ADDITIONAL_CSV_USERNAME_COL_INDEX] == username:
                modified = list(row)
                # clean data
                score = row[self.ADDITIONAL_CSV_SCORE_COL_INDEX]
                score = score.replace("\xd7", "")
                modified[self.ADDITIONAL_CSV_SCORE_COL_INDEX] = int(score)
                return modified
        return False

    def search_assignment_col(self, assignment_name, dataset):
        for i, h in enumerate(dataset.headers):
            if h.startswith(assignment_name):
                return i
        return False

    def handle(self, *args, **options):
        csv_path = options["csv"]
        csv2_path = options["csv2"]
        csv_new_path = options["new"]

        dataset = tablib.Dataset().load(open(csv_path).read())
        additional = tablib.Dataset().load(open(csv2_path).read())

        modified_data = tablib.Dataset()
        modified_data.headers = dataset.headers

        # Say hello to O(n^2)
        for row in dataset:
            if not len(row):
                continue
            # search username in additional csv and get related row
            username_col_index = dataset.headers.index("user_name")
            username = row[username_col_index]

            # Handle ALL related rows in additional dataset
            copied = list(row)
            for r in additional:
                if r[self.ADDITIONAL_CSV_USERNAME_COL_INDEX] == username:
                    additional_row = list(r)
                    # clean data
                    score = r[self.ADDITIONAL_CSV_SCORE_COL_INDEX]
                    score = score.replace("\xd7", "")
                    additional_row[self.ADDITIONAL_CSV_SCORE_COL_INDEX] = int(score)

                    assignment_name = additional_row[self.ADDITIONAL_CSV_ASSIGNMENT_NAME_COL_INDEX]
                    assignment_index = self.search_assignment_col(assignment_name, dataset)
                    if not assignment_index:
                        print("cant find assignment name {}".format(assignment_name))
                        continue
                    a_str = copied[assignment_index]
                    current_max_value, rest = a_str.split("(", 1)
                    # get diff with max score for assignment
                    diff = int(current_max_value) - additional_row[self.ADDITIONAL_CSV_SCORE_COL_INDEX]
                    copied[assignment_index] = str(additional_row[self.ADDITIONAL_CSV_SCORE_COL_INDEX]) + "(" + rest
                    # Update total score
                    score_col_index = dataset.headers.index("score")
                    copied[score_col_index] = str(int(copied[score_col_index]) - diff)
            modified_data.append(copied)

        with open(csv_new_path, 'wb') as f:
            f.write(modified_data.csv)