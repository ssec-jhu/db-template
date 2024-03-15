#!/bin/bash

conda activate biospecdb

cd repo/biospecdb
git fetch
git checkout origin/main -f

export DB_VENDOR=postgresql
export DJANGO_SETTINGS_MODULE=biospecdb.settings.aws

export $(python -c "from biospecdb.util import print_aws_secrets;print_aws_secrets()")
