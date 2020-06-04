import json


def extract_tags_from_response(response):
    json_obj = json.loads(response.content)
    return list(map(lambda el: el['text'], json_obj['results']))
