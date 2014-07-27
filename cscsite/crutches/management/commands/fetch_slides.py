from __future__ import unicode_literals, print_function

import re
import tempfile
import urllib
import urllib2

from django.conf import settings
from django.core.files import File
from django.core.management import BaseCommand
from django.db import transaction
from django.utils.encoding import force_text
from slideshare import SlideshareAPI

from learning.models import CourseClass, CourseClassAttachment

re_embed = re.compile("embed_code/(\d+)")


class Command(BaseCommand):
    help = ("Fetches slides from the SlideShare embed code "
            "for 'CourseClass' instances with no attached slides.")

    def handle(self, *args, **options):
        api = SlideshareAPI(settings.SLIDESHARE_API_KEY,
                            settings.SLIDESHARE_SECRET)

        course_classes = (CourseClass.objects
            .filter(slides="",  other_materials__contains="slideshare")
            .prefetch_related("course_offering")
            .only("other_materials"))

        # XXX in case of exception NOTHING will be modified.
        # YAY transactions.
        with transaction.atomic():
            for course_class in course_classes:
                assert not course_class.slides

                slideshare_ids = re_embed.findall(course_class.other_materials)
                print(force_text(course_class.course_offering),
                      force_text(course_class))
                print(*map(force_text, slideshare_ids))

                if not slideshare_ids:
                    continue

                # Only download the first slides (if multiple).
                slideshare_id = slideshare_ids[0]
                response = api.get_slideshow(slideshare_id,
                    username=settings.SLIDESHARE_USERNAME,
                    password=settings.SLIDESHARE_PASSWORD)
                slideshow = response["Slideshow"]
                download_url = slideshow["DownloadUrl"]

                f = tempfile.NamedTemporaryFile(delete=False)
                urllib.urlretrieve(download_url, f.name)
                f.flush()

                # 'CourseClass#upload_to' only uses the extension.
                dummy = "unused_name." + slideshow["Format"]
                course_class.slides.save(dummy, File(f))
                course_class.save()
                f.delete = True
                f.close()







