import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a production superuser from environment variables when one does not exist"

    def handle(self, *args, **options):
        email = (
            os.getenv("DJANGO_SUPERUSER_EMAIL")
            or os.getenv("ADMIN_EMAIL")
            or ""
        ).strip().lower()
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD") or os.getenv("ADMIN_PASSWORD") or ""

        if not email or not password:
            self.stdout.write(self.style.WARNING("Admin env vars not set. Skipping superuser creation."))
            return

        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first() or User.objects.filter(username__iexact=email).first()
        if user:
            changed = False
            if not user.is_staff:
                user.is_staff = True
                changed = True
            if not user.is_superuser:
                user.is_superuser = True
                changed = True
            if changed:
                user.save(update_fields=["is_staff", "is_superuser"])
                self.stdout.write(self.style.SUCCESS(f"Updated existing admin account: {email}"))
            else:
                self.stdout.write(self.style.WARNING(f"Admin account already exists: {email}"))
            return

        User.objects.create_superuser(username=email, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Created admin account: {email}"))
