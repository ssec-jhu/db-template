#!/bin/bash

ls

ls docs/

set -e

# Collect static files.
pipenv run python3 manage.py collectstatic --clear --noinput

# Drop SQL views before migration as views can't be migrated and thus block certain migrations.
pipenv run python3 manage.py update_sql_views --drop_only flat_view

# Migrate DB
mkdir -p db
pipenv run python3 manage.py migrate
pipenv run python3 manage.py migrate --database=bsr

# Load fixture seed data.
# Don't do this on deployment so as not to clobber any live alterations. Instead, call these manually from the ec2
# instance connected to the RDS instance.
#pipenv run python3 manage.py loaddata centers queries
#pipenv run python3 manage.py loaddata --database=bsr centers observables instruments qcannotators biosampletypes spectrameasurementtypes

# Update SQL views.
pipenv run python3 manage.py update_sql_views flat_view

# Install crontab.
pipenv run python3 manage.py crontab add

# Clean up orphaned files.
pipenv run python3 manage.py prune_files

# Create superuser.
pipenv run python3 manage.py makesuperuser --noinput --username=admin --email=admin@spadda.org --center=16721944-ff91-4adf-8fb3-323b99aba801

pipenv run gunicorn -c config/gunicorn/prd.py
