API_URL = 'https://api.contest.yandex.net/api/public/v2'
CONTEST_PARTICIPANTS_URL = API_URL + '/contests/{}/participants'


class YandexContestAPIException(Exception):
    pass
