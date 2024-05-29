#!/bin/bash

conda activate biodb

cd repo/biodb
git fetch
git checkout origin/main -f

export DB_VENDOR=postgresql
export DJANGO_SETTINGS_MODULE=biodb.settings.aws

export $(python -c "from biodb.util import print_aws_secrets;print_aws_secrets()")
