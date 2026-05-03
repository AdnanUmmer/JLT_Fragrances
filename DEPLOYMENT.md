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
- `DJANGO_SUPERUSER_EMAIL`
- `DJANGO_SUPERUSER_PASSWORD`
- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `DEFAULT_FROM_EMAIL`
- `OWNER_NOTIFICATION_EMAIL`

## 3. Render build and start commands

Use these commands on Render:

```bash
bash build.sh
```

```bash
bash start.sh
```

`start.sh` runs migrations, creates/updates a superuser only when `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD` are configured, imports `store/data/JLT_Perfumes_Updated.csv` only when the product table is empty, then starts Gunicorn. This keeps products visible after a fresh production database is created without deleting admin-entered data on later deploys.
Set `PRODUCT_CSV_PATH` on Render if you want to load a different CSV path.

## 4. Prepare the database and static files locally

```powershell
py manage.py migrate
py manage.py collectstatic --noinput
py manage.py import_csv --skip-if-products-exist
```

## 5. Run locally in production mode

```powershell
py -m gunicorn perfume_site.wsgi --bind 0.0.0.0:8000
```

## 6. Razorpay go-live checklist

- Use live Razorpay keys in production.
- Add your production domain in the Razorpay dashboard allowlist/settings.
- Complete at least one real payment test after deployment.
- Confirm webhook setup separately if you later add webhook-based reconciliation.
