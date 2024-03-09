# Delete initial migrations.
rm biospecdb/apps/user/migrations/0*
rm biospecdb/apps/uploader/migrations/0*
rm biospecdb/apps/catalog/migrations/0*

# Delete uploaded data files.
rm spectra_data/*
rm raw_data/*
rm datasets/*

# Delete databases.
dropdb admin
dropdb bsr

set -e

export DB_VENDOR=postgresql
export PGPASSWORD="123456789"

export DB_ADMIN_HOST="localhost"
export DB_ADMIN_PORT=5432
export DB_ADMIN_USER="admindbuser"
export DB_ADMIN_PASSWORD=$PGPASSWORD

export DB_BSR_HOST="localhost"
export DB_BSR_PORT=5432
export DB_BSR_USER="bsrdbuser"
export DB_BSR_PASSWORD=$PGPASSWORD

export DJANGO_SETTINGS_MODULE=biospecdb.settings.dev

# Collect all static files to be served.
# NOTE: `manage.py runserver` does this automatically, however, serving from gunicorn obviously doesn't.
python manage.py collectstatic --clear --noinput

# Redo migrations since they were deleted above.
python manage.py makemigrations

# Create DBs.
createdb admin
createdb bsr

# Drop users.
dropuser --if-exists $DB_ADMIN_USER
dropuser --if-exists $DB_BSR_USER

# create users.
createuser --superuser --no-password $DB_ADMIN_USER
createuser --superuser --no-password $DB_BSR_USER

# Migrate DBs.
python manage.py migrate
python manage.py migrate --database=bsr

# Load initial data fixtures.
python manage.py loaddata centers queries
python manage.py loaddata --database=bsr centers observables instruments qcannotators biosampletypes spectrameasurementtypes
python manage.py update_sql_views full_patient

# Creat superuser.
# Note: This center ID is that for the SSEC and the default password is "admin".
DJANGO_SUPERUSER_PASSWORD="${DJANGO_SUPERUSER_PASSWORD:-admin}" python manage.py createsuperuser --noinput --username=admin --email=admin@jhu.edu --center=d61f1c2a-9c0a-4309-a031-ab5b8d2106b0
