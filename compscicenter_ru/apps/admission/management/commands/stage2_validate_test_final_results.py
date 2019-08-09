# -*- coding: utf-8 -*-
import csv
from decimal import Decimal

from django.core.management import BaseCommand

from admission.models import Applicant, Test, Campaign, Contest
from api.providers.yandex_contest import YandexContestAPI, \
    YandexContestAPIException
from ._utils import CurrentCampaignsMixin


class Command(CurrentCampaignsMixin, BaseCommand):
    help = (
        """
        To make sure that all results across all contests were correctly 
        imported to our database, let's iterate over csv files exported from 
        contests and double check the results. Print out row for participants 
        whom not found in our database.
        """
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('csv', metavar='CSV',
                            help='Path to csv with results')

    def handle(self, *args, **options):
        csv_path = options["csv"]
        campaign_ids = self.get_current_campaign_ids(options)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        # Collect map "yandex_login -> participant_id" from monitor
        participants = {}
        campaign = Campaign.objects.filter(id__in=campaign_ids).first()
        api = YandexContestAPI(access_token=campaign.access_token)
        for contest in campaign.contests.filter(type=Contest.TYPE_TEST).all():
            contest_id = contest.contest_id
            paging = {
                "page_size": 50,
                "page": 1
            }
            scoreboard_total = 0
            while True:
                try:
                    status, json_data = api.standings(contest_id, **paging)
                    page_total = 0
                    for row in json_data['rows']:
                        scoreboard_total += 1
                        page_total += 1
                        yandex_login = row['participantInfo']['login']
                        participant_id = row['participantInfo']['id']
                        participants[yandex_login] = participant_id
                    if page_total < paging["page_size"]:
                        break
                    paging["page"] += 1
                except YandexContestAPIException as e:
                    error_status_code, text = e.args
                    print(f"проблемсы с апишкой {error_status_code}")

        with open(csv_path, "r") as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                total = int(Decimal(row['total'].replace(',', '.')))
                yandex_login = row['yandex_login']
                a = Applicant.objects.filter(campaign__in=campaign_ids,
                                             yandex_id=yandex_login)
                applicant = None
                exists = a.exists()
                if exists:
                    try:
                        applicant = a.get()
                        # Compare results
                        t = Test.objects.get(applicant_id=applicant.pk)
                        if t.score != total:
                            print(f"Не совпадают баллы для {yandex_login}: БД {t.score}, монитор: {total}. Ссылка на анкету {applicant.get_absolute_url()}")
                    except Applicant.MultipleObjectsReturned:
                        print(f"Multiple objects for yandex_login {yandex_login}")
                else:
                    if yandex_login not in participants:
                        print(f"Not found {yandex_login}")
                    else:
                        try:
                            t = Test.objects.select_related("applicant").get(contest_participant_id=participants[yandex_login])
                            print(f"Не найден логин {yandex_login}, но есть запись в контесте {t.yandex_contest_id} [participant_id {participants[yandex_login]}]. Ссылка на анкету {t.applicant.get_absolute_url()}")
                            applicant = t.applicant
                        except Test.DoesNotExist:
                            print(f"Вообще не найден {yandex_login} c participant_id {participants[yandex_login]}")

                if applicant is not None:
                    # Поиск дубликатор
                    similar = applicant.get_similar().filter(campaign_id__in=campaign_ids)
                    if similar.exists():
                        print(f"Дубликаты для {applicant}, yandex_login {yandex_login}. Анкета {applicant.get_absolute_url()}")
                        for a in similar:
                            print(f"    {a.get_absolute_url()}")
