# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import tablib
from dateutil import parser
from math import floor

from django.core.management import BaseCommand, CommandError
from django.utils import timezone

from learning.admission.models import Applicant, Exam, Interview, Comment, \
    Campaign
from learning.settings import PARTICIPANT_GROUPS
from users.models import CSCUser


class Command(BaseCommand):

    # TODO: Autocorrect yandex id (remove @ya.ru @yandex.ru and so on.)
    # TODO: convert course text value to CSCUser.COURSES numeric value?
    def add_arguments(self, parser):
        parser.add_argument('csv', metavar='CSV',
                   help='path to csv with data')
        parser.add_argument('--year', type=int,
                            dest='campaign_year',
                            help='Campaign year')

    def handle(self, *args, **options):
        csv_path = options["csv"]
        campaign_year = options["campaign_year"]

        try:
            campaign = Campaign.objects.get(code=campaign_year)
        except Campaign.DoesNotExist:
            raise CommandError("Campaign not found")

        status_map = {
            "Принят": "accept",
            "ОтказСоб": "rejected_interview",
            "ОтказЭкз": "rejected_exam",
            "Вольное слушание": "volunteer",
            "Иногородний": "rejected_interview",
            "Неактуально": "they_refused",
            "НеПришел": "rejected_exam",
            "Школьник": "rejected_interview",
        }

        reviewer_map = {
            "lilosea": 607,
            "andrey": 863,
            "kulikov": 5,
            "katya": 38,
            "nikita": 27,
            "ilya": 588,
            "avsmal": 32,
        }

        dataset = tablib.Dataset().load(open(csv_path).read())
        for row in dataset.dict:
            try:
                applicant = Applicant.objects.get(
                    uuid=row['uuid'],
                    campaign=campaign
                )
            except Applicant.DoesNotExist:
                where_did_you_learn = []
                if row["habr"] == 'X':
                    where_did_you_learn.append("хабр")
                if row["friends"] == 'X':
                    where_did_you_learn.append("друзья")
                if row["tandp"] == 'X':
                    where_did_you_learn.append("tandp")
                if row["vk"] == 'X':
                    where_did_you_learn.append("vk")
                if row["club"] == 'X':
                    where_did_you_learn.append("клуб")
                if row["ad"] == 'X':
                    where_did_you_learn.append("ad")
                if row["other"] == 'X':
                    where_did_you_learn.append("другое")
                applicant = Applicant(
                    campaign=campaign,
                    created=parser.parse(row["created"]),
                    first_name=row["first_name"],
                    second_name=row["second_name"],
                    last_name=row["last_name"],
                    email=row["email"],
                    phone=row["phone"],
                    university=row["university"],
                    faculty="<empty>",
                    course=row["course"],
                    graduate_work=row["graduate_work"],
                    experience=row["experience"],
                    preferred_study_programs="<empty>",
                    motivation=row["motivation"],
                    additional_info=row["additional_info"],
                    where_did_you_learn=";".join(where_did_you_learn),
                    uuid=row["uuid"],
                )
            # set status

            applicant.status = status_map.get(row["interview_result"])
            applicant.save()
            # Set exam results
            try:
                exam = Exam.objects.get(applicant=applicant)
            except Exam.DoesNotExist:
                try:
                    score = floor(float(row["exam_score"]))
                except:
                    score = 0
                exam = Exam(
                    score=score,
                    applicant=applicant
                )
                exam.save()
            # Create interview
            if row["interview_date"]:
                interview_date = parser.parse(row["interview_date"])
                try:
                    hour, minute = row["interview_time"].split(":")
                    interview_date = interview_date.replace(
                        hour=int(hour), minute=int(minute)
                    )
                except:
                    pass
                interview_date = timezone.make_aware(interview_date,
                                                     timezone.get_current_timezone())
                reviewers = []
                for reviewer in reviewer_map:
                    try:
                        score = row[reviewer]
                        score = floor(float(score))
                        reviewers.append(reviewer)
                    except (TypeError, ValueError):
                        pass

                try:
                    interview = Interview.objects.get(
                        date=interview_date,
                        status=Interview.COMPLETED,
                        applicant=applicant
                    )
                except Interview.DoesNotExist:
                    interview = Interview(
                        date=interview_date,
                        status=Interview.COMPLETED,
                        applicant=applicant,
                    )
                    interview.save()
                    interview.interviewers = [reviewer_map[x] for x in reviewers]
                    # Create comments
                    for reviewer in reviewers:
                        try:
                            reviewer_score = floor(float(row[reviewer]))
                        except:
                            reviewer_score = 0  # katya new comment
                        comment = Comment(
                            text="",
                            interview=interview,
                            interviewer_id=reviewer_map[reviewer],
                            score=floor(float(row[reviewer]))
                        )
                        comment.save()
                    # Append text to one of comment
                    comment.text = row["interview_comments"]
                    comment.save()

            if row["interview_confirm"]:
                try:
                    student = CSCUser.objects.get(
                        email=row["email"],
                        groups__in=[PARTICIPANT_GROUPS.STUDENT_CENTER,
                                    PARTICIPANT_GROUPS.GRADUATE_CENTER]
                    )
                    applicant.user = student
                    applicant.save()
                except:
                    pass




            # OrderedDict([('created', '5/10/2014 00:00:00'), ('Draft', ' 23:53'),
            #              ('IP адрес', '178.162.48.210'),
            #              ('second_name', 'Козар '), ('first_name', 'Анастасия'),
            #              ('last_name', 'Дмитриевна'), ('phone', '89218738688'),
            #              ('email', 'Nastya.shev9594@gmail.com'),
            #              ('university', 'Прикладная математика, Спбгпу'),
            #              ('course', '2'), ('graduate_work', ''),
            #              ('experience', ''), ('motivation', ''),
            #              ('additional_info', ''), ('friends', 'X'),
            #              ('habr', ''), ('tandp', ''), ('vk', ''), ('club', ''),
            #              ('ad', ''), ('other', ''), ('interview_date', ''),
            #              ('interview_time', ''), ('ВарЭкз', '587'), ('1', '1'),
            #              ('2', '0'), ('3', '0'), ('4', '0'), ('5', '0'),
            #              ('6', '0'), ('7', '0'), ('8', '0'), ('9', '0'),
            #              ('10', '0'), ('11', '0'), ('12', '0'),
            #              ('exam_score', '1'), ('lilosea', ''), ('andrey', ''),
            #              ('kulikov', ''), ('katya', ''), ('nikita', ''),
            #              ('ilya', ''), ('avsmal', ''),
            #              ('interview_result', 'ОтказЭкз'),
            #              ('interview_comments', ''), ('interview_confirm', ''),
            #              ('uuid', 'ce63f29f-0e3b-48ea-8158-836c681eeb3b')])
        print("Done")
