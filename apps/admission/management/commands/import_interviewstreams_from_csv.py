import csv
import datetime
from collections import defaultdict
from typing import Tuple

from django.db import transaction

from admission.constants import InterviewSections, InterviewFormats
from admission.models import InterviewStream, Campaign, InterviewFormat, InterviewSlot
from admission.utils import slot_range
from core.models import Location, Branch
from users.models import User

from django.conf import settings

from django.core.management import BaseCommand


class Command(BaseCommand):
    help = """Import interview streams from csv"""

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--filename",
            type=str,
            default='interviews.csv',
            help="csv file name",
        )
        parser.add_argument(
            "--delimiter",
            type=str,
            default=',',
            help="csv delimiter",
        )

    prefix = "Выбери время, когда ты сможешь провести собеседование."

    year = 2024
    with_assignments = False
    commit = True

    def get_month_number(self, month_name: str) -> int:
        return {
            "июня": 6,
            "июля": 7,
            "августа": 8
        }[month_name]

    def get_section(self, section_name: str) -> InterviewSections:
        return {
            "общая секция": InterviewSections.ALL_IN_ONE,
            "математика": InterviewSections.MATH,
            "код": InterviewSections.PROGRAMMING,
            "математика+код": InterviewSections.MATH_PROGRAMMING,
            "мотивация": InterviewSections.MOTIVATION
        }[section_name]

    def get_format(self, format: str) -> InterviewFormats:
        return {
            "очно": InterviewFormats.OFFLINE,
            "онлайн": InterviewFormats.ONLINE
        }[format]

    def get_stream_date(self, s: str, year: int) -> datetime.date:
        """Returns a date of the slot"""
        assert self.prefix in s
        dash = '/ '
        date_start_index = s.find(dash) + len(dash)
        date_end_index = date_start_index + 1
        if s[date_end_index] != ' ':
            date_end_index += 1
        day = int(s[date_start_index:date_end_index])
        month_start_index = date_end_index + 1
        month_end_index = s.find(' ', month_start_index)
        month = self.get_month_number(s[month_start_index:month_end_index])
        return datetime.date(day=day, month=month, year=year)

    def parse_time_pair(self, string: str) -> Tuple[datetime.time, datetime.time]:
        begin, end = string.split('-')
        begin = datetime.datetime.strptime(begin, '%H:%M').time()
        end = datetime.datetime.strptime(end, '%H:%M').time()
        return begin, end

    def get_stream_begin_end(self, s: str) -> Tuple[datetime.time, datetime.time]:
        """Returns a pair: begin and end time of available slot"""
        dash = '/ '
        second_occurrence = s.find(dash, s.find(dash) + len(dash))
        time_part = s[second_occurrence + len(dash):]
        return self.parse_time_pair(time_part)

    filial_cache = {}

    def get_filial_info(self, branch_name: str, format: InterviewFormats):
        if (branch_name, format) not in self.filial_cache:
            branch = Branch.objects.get(name=branch_name, site_id=settings.SITE_ID)
            campaign = Campaign.objects.get(branch=branch, current=True)
            venue_name = f'{"Онлайн" if format == InterviewFormats.ONLINE else "Офлайн" }-собеседование в ШАД' \
                         f' {branch_name} {self.year}'
            venue = Location.objects.get(name=venue_name)
            interview_format = InterviewFormat.objects.get(campaign=campaign, format=format)
            result = (campaign, venue, interview_format)
            self.filial_cache[(branch_name, format)] = result
        return self.filial_cache[(branch_name, format)]

    def handle(self, *args, **options):
        delimiter = options["delimiter"]
        filename = options["filename"]
        with open(filename) as csvfile:
            reader = csv.reader(csvfile, delimiter=delimiter)
            headers = next(reader)
            # Колонки с выбором времени
            slot_columns = [i for i, s in enumerate(headers) if self.prefix in s]
            streams = defaultdict(list)
            for row in reader:
                interviewer_mail = row[1]
                campaign_name = row[2]
                format = row[3]
                interviewer_section = row[4] + row[5] + row[6] + row[7]
                interviewers_max = int(row[8])
                interview_date, interview_start, interview_last_stamp = None, None, None
                for column in slot_columns:
                    if row[column]:
                        # Получаем дату и время начала/конца собеседования
                        begin, end = self.get_stream_begin_end(headers[column])
                        date = self.get_stream_date(headers[column], self.year)
                        if interview_start is None:
                            interview_date = date
                            interview_start = begin
                        elif interview_date != date:
                            # заполняем dict с потоками возможными временами
                            key = (interviewer_mail, interviewer_section, interview_date, campaign_name, format, interviewers_max)
                            streams[key].append((interview_start, interview_last_stamp))
                            interview_date = date
                            interview_start = begin
                        interview_last_stamp = end
                    elif interview_start is not None:
                        key = (interviewer_mail, interviewer_section, interview_date, campaign_name, format, interviewers_max)
                        streams[key].append((interview_start, interview_last_stamp))
                        interview_date, interview_start, interview_last_stamp = None, None, None
                if interview_start is not None:
                    key = (interviewer_mail, interviewer_section, interview_date, campaign_name, format, interviewers_max)
                    streams[key].append((interview_start, interview_last_stamp))
            begin, end = self.get_stream_begin_end(headers[slot_columns[0]])
            slot_size = (datetime.timedelta(hours=end.hour, minutes=end.minute) -
                         datetime.timedelta(hours=begin.hour, minutes=begin.minute))
            with transaction.atomic():
                for stream_info, slots_ranges in streams.items():
                    stream_begin, stream_end = slots_ranges[0][0], slots_ranges[-1][1]
                    assert stream_begin < stream_end
                    interviewer = User.objects.get(email__iexact=stream_info[0])
                    section = self.get_section(stream_info[1])
                    format = self.get_format(stream_info[4])
                    interviewers_max = stream_info[5]
                    campaign, venue, interview_format = self.get_filial_info(stream_info[3], format)
                    print(f'{stream_info[0]}, {campaign}, {format}, {section}, {stream_info[2]}, {stream_begin}-{stream_end}')
                    stream = InterviewStream(
                        campaign=campaign,
                        venue=venue,
                        format=format,
                        interview_format=interview_format,
                        section=section,
                        with_assignments=self.with_assignments,
                        date=stream_info[2],
                        start_at=stream_begin,
                        end_at=stream_end,
                        duration=slot_size.seconds // 60,
                        interviewers_max=interviewers_max
                    )
                    stream.save()
                    stream.interviewers.add(interviewer)
                    slots_that_should_be = {
                        start_at
                        for period in slots_ranges
                        for start_at, end_at in slot_range(period[0], period[1], slot_size)
                    }
                    all_slots = {start_at for start_at, end_at in slot_range(stream_begin, stream_end, slot_size)}
                    slots_for_delete = all_slots.difference(slots_that_should_be)
                    InterviewSlot.objects.filter(
                        stream=stream,
                        start_at__in=slots_for_delete
                    ).delete()
                if not self.commit:
                    raise Exception("Please set value commit = True")
