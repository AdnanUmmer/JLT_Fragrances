from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class LuxuryAccountAdapter(DefaultAccountAdapter):
    def populate_username(self, request, user):
        user.username = user.email


class LuxurySocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        user.username = user.email
        return user

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        profile = user.profile
        profile.google_account = True
        profile.save(update_fields=["google_account"])
        return user
