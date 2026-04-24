"""
ASGI config for perfume_site project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from perfume_site.python_bootstrap import bootstrap_local_packages
from django.core.asgi import get_asgi_application

bootstrap_local_packages()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perfume_site.settings')

application = get_asgi_application()
