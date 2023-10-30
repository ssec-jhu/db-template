# Delete initial migrations.
rm biospecdb/apps/user/migrations/0*
rm biospecdb/apps/uploader/migrations/0*

# Delete uploaded data files.
rm spectra_data/*
rm raw_data/*

# Delete databases.
mkdir -p db
rm db/*.sqlite3
# Delete older DB files during interim development, see https://github.com/ssec-jhu/biospecdb/issues/152.
rm *.sqlite3

set -e

# Redo migrations since they were deleted above.
python manage.py makemigrations user
python manage.py makemigrations uploader

# Create and/or migrate DBs.
python manage.py migrate
python manage.py migrate --database=bsr

# Load initial data fixtures.
python manage.py loaddata centers
python manage.py loaddata --database=bsr centers diseases instruments qcannotators
python manage.py update_sql_views

# Creat superuser.
# Note: This center ID is that for the SSEC and the default password is "admin".
DJANGO_SUPERUSER_PASSWORD="${DJANGO_SUPERUSER_PASSWORD:-admin}" python manage.py createsuperuser --noinput --username=admin --email=admin@jhu.edu --center=d61f1c2a-9c0a-4309-a031-ab5b8d2106b0
