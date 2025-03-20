import csv
import datetime
import io
import yadisk
from django.core.management import BaseCommand
from django.utils import timezone

from admission.models import Campaign
from admission.reports import ApplicantStatusLogsReport, AdmissionApplicantsYearReport
from api.models import ExternalServiceToken


class Command(BaseCommand):
    help = "Dump daily applicant status logs and yearly applicant data to yandex disk"

    def handle(self, *args, **options):
        # Get current year
        current_year = timezone.now().year
        
        # Upload applicant status logs
        self.upload_applicant_status_logs()
        
        # Upload yearly applicant report
        self.upload_applicant_year_report(current_year)
    
    def upload_applicant_status_logs(self):
        """Upload applicant status logs to Yandex Disk"""
        # Get report directly
        report = ApplicantStatusLogsReport()
        
        # Get CSV data
        with io.StringIO() as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(report.headers)
            
            for row in report.data:
                csv_writer.writerow(row)

            csv_file.seek(0)
            client = yadisk.Client(token=ExternalServiceToken.objects.get(service_tag="syrop_yandex_disk").access_key)
            with client:
                if not client.check_token():
                    raise AssertionError("Token seems to be invalid. Is it expired?")
                
                # Use ISO format for filename
                today = timezone.now().date().isoformat()
                client.upload(io.BytesIO(csv_file.getvalue().encode()), 
                              f"/ysda/daily_applicant_status_logs/applicant_status_logs_{today}.csv")
    
    def upload_applicant_year_report(self, year):
        """Upload yearly applicant report to Yandex Disk"""
        # Get report directly
        report = AdmissionApplicantsYearReport(year=year)
        
        # Get CSV data
        with io.StringIO() as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(report.headers)
            
            for row in report.data:
                csv_writer.writerow(row)

            csv_file.seek(0)
            client = yadisk.Client(token=ExternalServiceToken.objects.get(service_tag="syrop_yandex_disk").access_key)
            with client:
                if not client.check_token():
                    raise AssertionError("Token seems to be invalid. Is it expired?")
                
                # Use ISO format for filename
                today = timezone.now().date().isoformat()
                client.upload(io.BytesIO(csv_file.getvalue().encode()), 
                              f"/ysda/daily_applicant_reports/applicant_year_report_{year}_{today}.csv")
