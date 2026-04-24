"""
WSGI config for perfume_site project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from perfume_site.python_bootstrap import bootstrap_local_packages
from django.core.wsgi import get_wsgi_application

bootstrap_local_packages()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perfume_site.settings')

application = get_wsgi_application()
