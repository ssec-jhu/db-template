#!/bin/bash

set -e

# Collect static files.
pipenv run python3 manage.py collectstatic --clear --noinput

# Migrate DB
mkdir -p db
pipenv run python3 manage.py migrate
pipenv run python3 manage.py migrate --database=bsr

# Load fixture seed data.
pipenv run python3 manage.py loaddata centers queries
pipenv run python3 manage.py loaddata --database=bsr centers observables instruments qcannotators biosampletypes spectrameasurementtypes

# Update SQL views.
#pipenv run python3 manage.py update_sql_views

# Create superuser.
pipenv run python3 manage.py makesuperuser --noinput --username=admin --email=admin@spadda.org --center=16721944-ff91-4adf-8fb3-323b99aba801

pipenv run gunicorn -c config/gunicorn/prd.py
