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
6. Start Django admin and create a `SocialApp`:
   - Provider: Google
   - Name: Google
   - Client id: your Google client ID
   - Secret key: your Google client secret
   - Sites: attach the current site

## Notes

- Login now uses email as identity.
- Internally, username is set to the email.
- Wishlist, checkout, and buy now now require sign-in.
- Guest wishlist clicks open the premium auth modal.
- Checkout creates an order and can save the address to the account.
