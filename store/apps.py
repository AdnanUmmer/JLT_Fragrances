import threading

from django.apps import AppConfig
from django.db.models.signals import post_migrate


_startup_bootstrap_scheduled = False


class StoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'store'

    def ready(self):
        global _startup_bootstrap_scheduled

        from . import signals  # noqa: F401
        from .social_bootstrap import ensure_google_social_app

        def bootstrap_google_social_app(sender=None, **kwargs):
            ensure_google_social_app(source="post_migrate")

        post_migrate.connect(bootstrap_google_social_app, sender=self)
        if not _startup_bootstrap_scheduled:
            _startup_bootstrap_scheduled = True
            threading.Timer(0.1, ensure_google_social_app, kwargs={"source": "startup"}).start()
