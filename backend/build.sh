#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
playwright install chromium --with-deps
python manage.py collectstatic --no-input
python manage.py migrate