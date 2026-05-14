from urllib.parse import quote

from django.conf import settings
from django.db import DatabaseError


def auth_nav(request):
    user = request.user
    display_name = ""
    if user.is_authenticated:
        display_name = user.first_name or user.get_full_name() or user.email.split("@")[0]
    return {"nav_display_name": display_name}


def site_settings(request):
    number = getattr(settings, "WHATSAPP_NUMBER", "") or ""
    message = getattr(
        settings,
        "WHATSAPP_MESSAGE",
        "Hello JLT Fragrances, I would like help choosing a perfume.",
    )

    try:
        from .models import SiteSetting

        site_setting = SiteSetting.objects.first()
        if site_setting:
            number = site_setting.whatsapp_number or number
            message = site_setting.whatsapp_message or message
    except DatabaseError:
        pass

    clean_number = "".join(ch for ch in number if ch.isdigit())
    whatsapp_url = ""
    if clean_number:
        whatsapp_url = f"https://wa.me/{clean_number}?text={quote(message)}"

    return {
        "site_whatsapp_number": number,
        "site_whatsapp_url": whatsapp_url,
    }
