import logging
from urllib.parse import urlparse

from django.conf import settings
from django.db import OperationalError, ProgrammingError, connection, transaction

logger = logging.getLogger(__name__)


REQUIRED_TABLES = {
    "django_site",
    "socialaccount_socialapp",
    "socialaccount_socialapp_sites",
}


def _site_domain():
    if settings.SITE_BASE_URL:
        parsed = urlparse(settings.SITE_BASE_URL)
        if parsed.netloc:
            return parsed.netloc

    render_host = getattr(settings, "RENDER_EXTERNAL_HOSTNAME", "") or ""
    if render_host:
        return render_host

    return "localhost"


def _required_tables_exist():
    return REQUIRED_TABLES.issubset(set(connection.introspection.table_names()))


def ensure_google_social_app(source="startup"):
    try:
        if not _required_tables_exist():
            logger.info("Google SocialApp bootstrap skipped during %s; database tables are not ready.", source)
            return False

        client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
        client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            logger.warning(
                "Google SocialApp bootstrap skipped during %s; GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is missing.",
                source,
            )
            return False

        from allauth.socialaccount.models import SocialApp
        from django.contrib.sites.models import Site

        with transaction.atomic():
            site, site_created = Site.objects.get_or_create(
                pk=settings.SITE_ID,
                defaults={"domain": _site_domain(), "name": "JLT Fragrances"},
            )

            app = SocialApp.objects.filter(provider="google").order_by("id").first()
            created = app is None
            if created:
                app = SocialApp(provider="google", name="Google")

            app.name = app.name or "Google"
            if created or not app.client_id:
                app.client_id = client_id
            if created or not app.secret:
                app.secret = client_secret
            app.key = ""
            app.save()
            app.sites.add(site)

        if created:
            logger.info("Google SocialApp created successfully during %s and attached to Site ID %s.", source, site.id)
        else:
            logger.info("Google SocialApp already exists during %s; Site ID %s attachment verified.", source, site.id)

        if site_created:
            logger.info("Site ID %s created for Google OAuth with domain %s.", site.id, site.domain)

        duplicate_count = SocialApp.objects.filter(provider="google").count()
        if duplicate_count > 1:
            logger.warning("Multiple Google SocialApps exist (%s). Bootstrap did not create duplicates.", duplicate_count)

        return True
    except (OperationalError, ProgrammingError) as exc:
        logger.warning("Google SocialApp bootstrap skipped during %s because the database is unavailable: %s", source, exc)
        return False
    except Exception:
        logger.exception("Google SocialApp bootstrap failed during %s.", source)
        return False
