import csv

from django.db import transaction
from django.db.models import Q

from core.models import Branch, Site

from users.constants import GenderTypes
from users.models import PartnerTag, User, StudentTypes
from users.services import create_account, generate_username_from_email, get_student_profile, create_student_profile

msk_branch = Branch.objects.get(pk=7)
msk_site = Site.objects.get(pk=3)

def extract_credentials(credentials: str):
    data = credentials.split(" ")
    if len(data) == 2:
        data.append("")
    return data[0], data[1], data[2]


def main():
    print(f"Branch: {msk_branch}")
    print(f"Site: {msk_site}")
    gender = GenderTypes.OTHER
    partner = PartnerTag.objects.get(pk=2)  # МФТИ=1, ФКН=2
    with open("students_fkn.csv", "r") as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        next(reader, None)  # skip the headers
        with transaction.atomic():
            for row in reader:
                last_name, first_name, patronymic = extract_credentials(row[0])
                email, track = row[1], row[2]
                try:
                    user = User.objects.get(email__iexact=email)
                    print(f"Found user {user} {track}")
                except User.DoesNotExist as e:
                    user = create_account(username=generate_username_from_email(email),
                                          password=User.objects.make_random_password(),
                                          email=email,
                                          gender=gender,
                                          time_zone=msk_branch.time_zone,
                                          is_active=True)
                    user.first_name = first_name
                    user.last_name = last_name
                    user.patronymic = patronymic
                    user.save()
                    print(f"CREATED USER {user} ({track})")

                if track == "базовый":
                    profile = get_student_profile(user=user,
                                                  site=msk_site,
                                                  profile_type=StudentTypes.REGULAR)
                    if profile is not None:
                        print(f"Found REGULAR profile {profile}: {profile.status}")
                    else:
                        profile_fields = {
                            "profile_type": StudentTypes.REGULAR,
                            "year_of_curriculum": 2022,
                            "user": user,
                            "branch": msk_branch,
                            "year_of_admission": 2022,
                            "partner": partner
                        }
                        profile = create_student_profile(**profile_fields)
                        print(f"CREATED REGULAR PROFILE: {profile}")

                profile = get_student_profile(user=user,
                                              site=msk_site,
                                              profile_type=StudentTypes.PARTNER)
                if profile is not None:
                    print(f"ATTENTION! Found PARTNER profile: {profile}: {profile.status}")
                else:
                    profile_fields = {
                        "profile_type": StudentTypes.PARTNER,
                        "year_of_curriculum": 2022,
                        "user": user,
                        "branch": msk_branch,
                        "year_of_admission": 2022,
                        "partner": partner
                    }
                    profile = create_student_profile(**profile_fields)
                    print(f"CREATED PARTNER PROFILE: {profile}")


main()
