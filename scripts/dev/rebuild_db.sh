rm biospecdb/apps/user/migrations/0*
rm biospecdb/apps/uploader/migrations/0*
rm admin.sqlite3 bsr.sqlite3

set -e

python manage.py makemigrations user
python manage.py makemigrations uploader

python manage.py migrate
python manage.py migrate --database=bsr

python manage.py loaddata centers
python manage.py loaddata --database=bsr centers diseases instruments qcannotators
python manage.py update_sql_views

# Note: This center ID is that for the SSEC.
python manage.py createsuperuser --username=admin --email=admin@jhu.edu --center=d61f1c2a-9c0a-4309-a031-ab5b8d2106b0
