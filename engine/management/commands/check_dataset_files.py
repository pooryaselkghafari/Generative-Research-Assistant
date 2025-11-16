"""
Management command to check dataset files and their paths.
"""
from django.core.management.base import BaseCommand
from engine.models import Dataset
from engine.encrypted_storage import is_encrypted_file
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Check dataset files and verify their paths'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dataset-id',
            type=int,
            help='Check a specific dataset by ID',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Check all datasets',
        )

    def handle(self, *args, **options):
        if options['dataset_id']:
            datasets = Dataset.objects.filter(pk=options['dataset_id'])
        elif options['all']:
            datasets = Dataset.objects.all()
        else:
            self.stdout.write(self.style.ERROR("Please specify --dataset-id or --all"))
            return

        if not datasets.exists():
            self.stdout.write(self.style.WARNING("No datasets found"))
            return

        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(f"Checking {datasets.count()} dataset(s)")
        self.stdout.write(f"{'='*80}\n")

        for dataset in datasets:
            self.stdout.write(f"\nDataset ID: {dataset.id}")
            self.stdout.write(f"Name: {dataset.name}")
            self.stdout.write(f"User: {dataset.user.username if dataset.user else 'No User'}")
            self.stdout.write(f"File Path: {dataset.file_path}")
            
            # Check if path is absolute or relative
            if os.path.isabs(dataset.file_path):
                full_path = dataset.file_path
            else:
                # Try relative to MEDIA_ROOT
                full_path = os.path.join(settings.MEDIA_ROOT, dataset.file_path)
            
            self.stdout.write(f"Full Path: {full_path}")
            
            # Check if file exists
            if os.path.exists(full_path):
                file_size = os.path.getsize(full_path)
                self.stdout.write(self.style.SUCCESS(f"✅ File exists ({file_size:,} bytes)"))
                
                # Check if encrypted
                if is_encrypted_file(full_path):
                    self.stdout.write(self.style.WARNING("🔒 File is ENCRYPTED"))
                else:
                    self.stdout.write("📄 File is NOT encrypted")
            else:
                self.stdout.write(self.style.ERROR("❌ File NOT FOUND"))
                
                # Try alternative locations
                alt_paths = [
                    dataset.file_path,  # Try as-is
                    os.path.join(settings.MEDIA_ROOT, 'datasets', os.path.basename(dataset.file_path)),
                    os.path.join('/app/media/datasets', os.path.basename(dataset.file_path)),
                ]
                
                for alt_path in alt_paths:
                    if alt_path != full_path and os.path.exists(alt_path):
                        self.stdout.write(self.style.SUCCESS(f"✅ Found at alternative path: {alt_path}"))
                        break
            
            self.stdout.write("-" * 80)

