from django.conf import settings
from django.core.management.base import BaseCommand

from store.views import _send_owner_email_notification


class Command(BaseCommand):
    help = "Send a test owner notification email using the current SMTP configuration."

    def add_arguments(self, parser):
        parser.add_argument('--to', dest='recipient', default='', help='Optional override recipient email address.')

    def handle(self, *args, **options):
        recipient = (options.get('recipient') or settings.OWNER_NOTIFICATION_EMAIL or '').strip()
        if not recipient:
            self.stderr.write(self.style.ERROR('OWNER_NOTIFICATION_EMAIL is not configured. Add it to .env or pass --to.'))
            return

        original_recipient = settings.OWNER_NOTIFICATION_EMAIL
        settings.OWNER_NOTIFICATION_EMAIL = recipient
        try:
            sent = _send_owner_email_notification(
                'JLT Fragrances test email',
                'This is a test email from the JLT Fragrances notification system.',
                ['test-email'],
            )
        finally:
            settings.OWNER_NOTIFICATION_EMAIL = original_recipient

        if sent:
            self.stdout.write(self.style.SUCCESS(f'Test email sent successfully to {recipient}.'))
            return

        self.stderr.write(self.style.ERROR(f'Test email failed for {recipient}. Check logs for the exact reason.'))
