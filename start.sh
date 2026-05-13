#!/usr/bin/env bash
set -o errexit

python manage.py migrate --noinput
python manage.py ensure_superuser
python manage.py import_csv --path "${PRODUCT_IMPORT_PATH:-${PRODUCT_CSV_PATH:-store/data/JLT_Perfume_List.xlsx}}" --replace-catalog
python -m gunicorn perfume_site.wsgi:application --log-file -
