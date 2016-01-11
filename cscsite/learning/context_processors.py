from learning import settings


def redirect_bases(request):
    # return any necessary values
    return {'LEARNING_BASE': settings.LEARNING_BASE,
            'TEACHING_BASE': settings.TEACHING_BASE}
