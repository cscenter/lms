import pytest

from django.contrib.sites.models import Site
from django.http.response import Http404

from core.middleware import CurrentCityMiddleware
from learning.factories import CourseOfferingFactory


@pytest.mark.django_db
def test_current_city_middleware(rf, settings, mocker):
    domain = "kzn.compsciclub.ru"
    request = rf.request()
    request.site = mocker.Mock(spec=Site)
    request.site.domain = domain
    request.META['HTTP_HOST'] = "{}:8000".format(domain)
    request.path = '/'
    assert not hasattr(request, "city_code")
    middleware = CurrentCityMiddleware(mocker.stub(name='get_response'))
    # No `city_aware` keyword, so parse sub domain
    middleware.process_view(request, view_func=lambda: "", view_args=[], view_kwargs={})
    assert hasattr(request, "city_code")
    assert request.city_code == "kzn"
    # Set default host
    domain = "compscicenter.ru"
    request.site.domain = domain
    request.META['HTTP_HOST'] = "{}:8000".format(domain)
    delattr(request, "city_code")
    middleware.process_view(request, view_func=lambda: "", view_args=[], view_kwargs={})
    assert request.city_code == "spb"
    assert settings.DEFAULT_CITY_CODE == "spb"

    co = CourseOfferingFactory(city_id="kzn", meta_course__slug="test")
    assert co.get_absolute_url() == "/courses/test/kzn/{}/".format(co.semester.slug)
    request.path = co.get_absolute_url()
    # Without `city_aware` url keyword we still should parse sub domain
    delattr(request, "city_code")
    middleware.process_view(request, view_func=lambda: "", view_args=[],
                            view_kwargs={})
    assert request.city_code == "spb"
    # Now set `city_aware`
    assert co.city_id == "kzn"
    view_kwargs = dict(city_aware=True, city_code="kzn", city_delimiter="/")
    middleware.process_view(request, view_func=lambda: "", view_args=[],
                            view_kwargs=view_kwargs)
    assert request.city_code == "kzn"
    # Test corner cases
    with pytest.raises(Http404):
        # Delimiter can't be empty for non-default city code
        view_kwargs = dict(city_aware=True, city_code="kzn", city_delimiter="")
        assert view_kwargs["city_code"] != settings.DEFAULT_CITY_CODE
        middleware.process_view(request, view_func=lambda: "", view_args=[],
                                view_kwargs=view_kwargs)
    with pytest.raises(Http404):
        # Delimiter should be empty for default city code
        view_kwargs = dict(city_aware=True, city_code="", city_delimiter="/")
        middleware.process_view(request, view_func=lambda: "",
                                view_args=[], view_kwargs=view_kwargs)
    domain = "kzn.compscicenter.ru"
    request.site.domain = domain
    request.META['HTTP_HOST'] = "{}:8000".format(domain)
    # Return default city code if `city_aware=True`
    view_kwargs = dict(city_aware=True, city_code="", city_delimiter="")
    middleware.process_view(request, view_func=lambda: "",
                            view_args=[], view_kwargs=view_kwargs)
    assert request.city_code == settings.DEFAULT_CITY_CODE
    # Unknown city_code passed, raise 404
    view_kwargs = dict(city_aware=True, city_code="wtf", city_delimiter="/")
    with pytest.raises(Http404):
        middleware.process_view(request, view_func=lambda: "",
                                view_args=[], view_kwargs=view_kwargs)
    # For wrong sub domain fallback to default city, makes sense for `www`.
    # In fact, we should fail on dns level if something like
    # `wtf.compscicenter.ru` were provided
    domain = "nsk.compscicenter.ru"
    request.site.domain = domain
    request.META['HTTP_HOST'] = "{}:8000".format(domain)
    view_kwargs = dict(city_aware=False, city_code="kzn", city_delimiter="/")
    middleware.process_view(request, view_func=lambda: "",
                            view_args=[], view_kwargs=view_kwargs)
    assert request.city_code == "nsk"
    # For compsciclub.ru always resolve sub domain
    settings.SITE_ID = settings.CLUB_SITE_ID
    domain = "kzn.compsciclub.ru"
    request.site.domain = domain
    request.META['HTTP_HOST'] = "{}:8000".format(domain)
    view_kwargs = dict(city_aware=True, city_code="nsk", city_delimiter="/")
    with pytest.raises(Http404):
        # We don't support `city_code` for compsciclub.ru , it must be empty
        middleware.process_view(request, view_func=lambda: "",
                                view_args=[], view_kwargs=view_kwargs)
    view_kwargs = dict(city_aware=True, city_code="", city_delimiter="")
    middleware.process_view(request, view_func=lambda: "",
                            view_args=[], view_kwargs=view_kwargs)
    assert request.city_code == "kzn"
