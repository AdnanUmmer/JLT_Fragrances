# Deployment Notes

## Local development

This project is pinned to Python 3.11 locally.

Because some Microsoft Store Python installs create a broken `venv` launcher on Windows, this repo includes a local bootstrap that loads packages from `.venv\Lib\site-packages` and a helper script:

```powershell
.\runserver.ps1
```

You can also use:

```powershell
.\python311.ps1 manage.py check
.\pip311.ps1 install --no-user --upgrade --target .\.venv\Lib\site-packages -r requirements.txt
```

## 1. Install dependencies

```powershell
pip install -r requirements.txt
```

## 2. Configure environment

Copy `.env.example` to `.env` and set:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `DEFAULT_FROM_EMAIL`
- `OWNER_NOTIFICATION_EMAIL`

## 3. Prepare the database and static files

```powershell
py manage.py migrate
py manage.py collectstatic --noinput
```

## 4. Run locally in production mode

```powershell
py -m gunicorn perfume_site.wsgi --bind 0.0.0.0:8000
```

## 5. Razorpay go-live checklist

- Use live Razorpay keys in production.
- Add your production domain in the Razorpay dashboard allowlist/settings.
- Complete at least one real payment test after deployment.
- Confirm webhook setup separately if you later add webhook-based reconciliation.
