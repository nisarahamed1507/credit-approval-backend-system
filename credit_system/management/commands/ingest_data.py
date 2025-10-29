from django.core.management.base import BaseCommand
from credit_system.tasks import ingest_all_data


class Command(BaseCommand):
    help = 'Ingest customer and loan data from Excel files'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data ingestion...'))
        
        # Run the task
        result = ingest_all_data.delay()
        
        self.stdout.write(self.style.SUCCESS(f'Data ingestion task started with ID: {result.id}'))
        self.stdout.write(self.style.SUCCESS('You can check the Celery logs for progress'))
