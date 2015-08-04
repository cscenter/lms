def check_for_city(city_code):
    from core.models import City
    try:
       x = City.objects.get(code=city_code)
    except City.DoesNotExist:
       x = None
    return x
    