import csv
import datetime
from collections import defaultdict
from typing import Tuple

from django.db import transaction

from admission.constants import InterviewSections, InterviewFormats
from admission.models import InterviewStream, Campaign, InterviewFormat, InterviewSlot
from admission.utils import slot_range
from core.models import Location
from users.models import User

prefix = "Выбери время, когда ты сможешь провести собеседование."

MONTH_NUMBER = {
    'июня': 6,
    'июля': 7,
    'августа': 8
}


def get_stream_date(s: str, year: int) -> datetime.date:
    assert prefix in s
    date_start_index = 0
    date_end_index = date_start_index + 1
    if s[date_start_index + 1] != ' ':
        date_end_index += 1
    day = int(s[date_start_index:date_end_index])
    month_start_index = date_end_index + 1
    month_end_index = s.find('.')
    month = MONTH_NUMBER[s[month_start_index:month_end_index]]
    return datetime.date(day=day, month=month, year=year)


def parse_time_pair(string) -> Tuple[datetime.time, datetime.time]:
    begin, _, end = string.split(' ')
    begin = datetime.datetime.strptime(begin, '%H:%M').time()
    end = datetime.datetime.strptime(end, '%H:%M').time()
    return begin, end


def get_stream_begin_end(s: str):
    prefix = '/ '
    time_part = s[s.find(prefix) + len(prefix):]
    return parse_time_pair(time_part)


def get_section(section_name: str) -> InterviewSections:
    return {
        "общая секция": InterviewSections.ALL_IN_ONE,
        "математика": InterviewSections.MATH,
        "код": InterviewSections.PROGRAMMING,
        "мотивация": InterviewSections.MOTIVATION
    }[section_name]


msk_campaign = Campaign.objects.get(pk=42)
msk_venue = Location.objects.get(pk=87)
msk_format = InterviewFormat.objects.get(pk=31)

distant_campaign = Campaign.objects.get(pk=48)
distant_venue = Location.objects.get(pk=105)
distant_format = InterviewFormat.objects.get(pk=32)

spb_campaign = Campaign.objects.get(pk=43)
spb_venue = Location.objects.get(pk=106)
spb_format = InterviewFormat.objects.get(pk=33)


def get_filial_info(campaign_name: str) -> Campaign:
    return {
        "Москва": (msk_campaign, msk_venue, msk_format),
        "Заочное": (distant_campaign, distant_venue, distant_format),
        "Санкт-Петербург": (spb_campaign, spb_venue, spb_format),
    }[campaign_name]


def main():
    year = 2023
    format = InterviewFormats.ONLINE
    with_assignments = False
    commit = True
    with open('interviews.csv') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        headers = next(reader)
        slot_columns = [i for i, s in enumerate(headers) if prefix in s]
        streams = defaultdict(list)
        for row in reader:
            interviewer_mail = row[1]
            campaign_name = row[2]
            interviewer_section = row[3] + row[4] + row[5]
            interview_date, interview_start, interview_last_stamp = None, None, None
            for column in slot_columns:
                if row[column]:
                    begin, end = get_stream_begin_end(headers[column])
                    date = get_stream_date(headers[column], year)
                    if interview_start is None:
                        interview_date = get_stream_date(headers[column], year)
                        interview_start = begin
                    elif interview_date != date:
                        key = (interviewer_mail, interviewer_section, interview_date, campaign_name)
                        streams[key].append((interview_start, interview_last_stamp))
                        interview_date = get_stream_date(headers[column], year)
                        interview_start = begin
                    interview_last_stamp = end
                elif interview_start is not None:
                    key = (interviewer_mail, interviewer_section, interview_date, campaign_name)
                    streams[key].append((interview_start, interview_last_stamp))
                    interview_date, interview_start, interview_last_stamp = None, None, None
            if interview_start is not None:
                key = (interviewer_mail, interviewer_section, interview_date, campaign_name)
                streams[key].append((interview_start, interview_last_stamp))
        begin, end = get_stream_begin_end(headers[slot_columns[0]])
        slot_size = (datetime.timedelta(hours=end.hour, minutes=end.minute) -
                     datetime.timedelta(hours=begin.hour, minutes=begin.minute))
        with transaction.atomic():
            for stream_info, slots_ranges in streams.items():
                stream_begin, stream_end = slots_ranges[0][0], slots_ranges[-1][1]
                assert stream_begin < stream_end
                print(stream_info[0])
                interviewer = User.objects.get(email__iexact=stream_info[0])
                section = get_section(stream_info[1])
                campaign, venue, interview_format = get_filial_info(stream_info[3])
                stream = InterviewStream(
                    campaign=campaign,
                    venue=venue,
                    format=format,
                    interview_format=interview_format,
                    section=section,
                    with_assignments=with_assignments,
                    date=stream_info[2],
                    start_at=stream_begin,
                    end_at=stream_end,
                    duration=slot_size.seconds // 60
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
            if not commit:
                raise Exception("Please set value commit = True")


main()
