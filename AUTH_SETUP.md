# Premium Luxury Auth Setup

## Install dependency

```bash
pip install django-allauth
```

## Run migrations

```bash
python manage.py migrate
```

## Google OAuth setup

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select your project.
3. Configure the OAuth consent screen.
4. Create an OAuth 2.0 Client ID for a web application.
5. Add these redirect URIs:
   - `http://127.0.0.1:8000/accounts/google/login/callback/`
   - `http://localhost:8000/accounts/google/login/callback/`
   - Your production callback, for example `https://yourdomain.com/accounts/google/login/callback/`
6. Set these environment variables locally and on Render:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
7. Run migrations. The app automatically creates or updates the Google `SocialApp` and attaches it to Site ID 1.
8. You can verify the configuration in Django admin at `/admin/socialaccount/socialapp/`.

## Notes

- Login now uses email as identity.
- Internally, username is set to the email.
- Wishlist, checkout, and buy now now require sign-in.
- Guest wishlist clicks open the premium auth modal.
- Checkout creates an order and can save the address to the account.
