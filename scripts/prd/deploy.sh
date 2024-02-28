#!/bin/bash

set -e

pipenv run python3 manage.py collectstatic --clear --noinput
pipenv run gunicorn -c config/gunicorn/prd.py
