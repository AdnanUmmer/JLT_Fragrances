#!/usr/bin/env bash
set -o errexit

python manage.py migrate --noinput
python manage.py ensure_superuser
python manage.py import_csv --path "${PRODUCT_CSV_PATH:-store/data/JLT_Perfumes_Updated.csv}" --skip-if-products-exist
python -m gunicorn perfume_site.wsgi:application --log-file -
