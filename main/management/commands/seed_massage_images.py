"""
Django management command: seed_massage_images

Usage:
1. Place images in main/static/images/massage_seed/ named as <id>.jpg, <id>.png, <id>.jpeg, or <id>.webp (where <id> is the Massage id).
2. Run: python manage.py seed_massage_images

This will copy images to Massage.image (upload_to='massage_images/') for massages that are missing images or whose image file is missing.
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from main.models import Massage
from django.core.files import File

SEED_DIR = os.path.join(settings.BASE_DIR, 'main', 'static', 'images', 'massage_seed')
SUPPORTED_EXTS = ['.jpg', '.jpeg', '.png', '.webp']

class Command(BaseCommand):
    help = 'Seed Massage images from static/images/massage_seed/'

    def handle(self, *args, **options):
        if not os.path.isdir(SEED_DIR):
            self.stdout.write(self.style.ERROR(f'Seed directory not found: {SEED_DIR}'))
            return
        updated, skipped = 0, 0
        for massage in Massage.objects.all():
            image_exists = False
            if massage.image:
                image_path = os.path.join(settings.MEDIA_ROOT, massage.image.name)
                image_exists = os.path.isfile(image_path)
            if image_exists:
                self.stdout.write(f'Skip id={massage.id}: image exists')
                skipped += 1
                continue
            # Try to find a seed image for this id
            found = False
            for ext in SUPPORTED_EXTS:
                seed_path = os.path.join(SEED_DIR, f'{massage.id}{ext}')
                if os.path.isfile(seed_path):
                    with open(seed_path, 'rb') as f:
                        fname = f'{massage.id}{ext}'
                        massage.image.save(fname, File(f), save=True)
                    self.stdout.write(self.style.SUCCESS(f'Updated id={massage.id} with {fname}'))
                    updated += 1
                    found = True
                    break
            if not found:
                self.stdout.write(f'Skip id={massage.id}: no seed image found')
                skipped += 1
        self.stdout.write(self.style.SUCCESS(f'Done. Updated: {updated}, Skipped: {skipped}'))
