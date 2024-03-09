# Delete initial migrations.
rm biospecdb/apps/user/migrations/0*
rm biospecdb/apps/uploader/migrations/0*
rm biospecdb/apps/catalog/migrations/0*

# Delete uploaded data files.
rm spectra_data/*
rm raw_data/*
rm datasets/*

# Delete databases.
mkdir -p db
rm db/*.sqlite3

set -e

export DB_VENDOR=sqlite
export DJANGO_SETTINGS_MODULE=biospecdb.settings.dev

# Collect all static files to be served.
# NOTE: `manage.py runserver` does this automatically, however, serving from gunicorn obviously doesn't.
python manage.py collectstatic --clear --noinput

# Redo migrations since they were deleted above.
python manage.py makemigrations

# Create and/or migrate DBs.
python manage.py migrate
python manage.py migrate --database=bsr

# Load initial data fixtures.
python manage.py loaddata centers queries
python manage.py loaddata --database=bsr centers observables instruments qcannotators biosampletypes spectrameasurementtypes
python manage.py update_sql_views full_patient

# Creat superuser.
# Note: This center ID is that for the spadda and the default password is "admin".
DJANGO_SUPERUSER_PASSWORD="${DJANGO_SUPERUSER_PASSWORD:-admin}" python manage.py createsuperuser --noinput --username=admin --email=admin@jhu.edu --center=16721944-ff91-4adf-8fb3-323b99aba801
