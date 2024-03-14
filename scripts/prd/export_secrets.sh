#!/bin/bash

# When adding/editing secrets, remember to also do so in apprunner.yaml

get_secret() {
  secret=$(aws secretsmanager get-secret-value --secret-id --query 'SecretString' $1)
  secret="${secret%\"}"
  secret="${secret#\"}"
  echo "$secret"
}

export DB_VENDOR=postgresql
export DJANGO_SETTINGS_MODULE=biospecdb.settings.aws

export DB_BSR_HOST=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:DB_BSR_HOST-Hq7aa9)
export DB_ADMIN_HOST=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:DB_ADMIN_HOST-NTlDxu)
export DB_BSR_USER=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:DB_BSR_USER-EjV5uT)
export DB_BSR_PORT=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:DB_BSR_PORT-mADIze)
export DB_ADMIN_USER=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:DB_ADMIN_USER-n4WHdp)
export DB_ADMIN_PORT=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:DB_ADMIN_PORT-M0eK1j)
export DB_BSR_PASSWORD=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:DB_BSR_PASSWORD-xEoYOO)
export DB_ADMIN_PASSWORD=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:DB_ADMIN_PASSWORD-NdWuLS)
export SECRET_KEY=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:SECRET_KEY-V3ABiP)
export DJANGO_SUPERUSER_PASSWORD=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:DJANGO_SUPERUSER_PASSWORD-baCj9f)
export N_WORKERS=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:N_WORKERS-HWBWTb)
export AWS_STORAGE_BUCKET_NAME=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:AWS_STORAGE_BUCKET_NAME-s1Fcyv)
export AWS_S3_REGION_NAME=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:AWS_S3_REGION_NAME-o1dcFN)
export SESSION_COOKIE_AGE=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:SESSION_COOKIE_AGE-mCp6jQ)
export HOST_DOMAIN=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:HOST_DOMAIN-VzvGf8)
export DB_BSR_PASSWORD_READONLY=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:DB_BSR_PASSWORD_READONLY-qFuKvJ)
export DB_BSR_USER_READONLY=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:DB_BSR_USER_READONLY-wtGBhZ)
export EMAIL_HOST=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:EMAIL_HOST-x2J4ik)
export EMAIL_HOST_USER=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:EMAIL_HOST_USER-s7GAZD)
export EMAIL_HOST_PASSWORD=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:EMAIL_HOST_PASSWORD-kPI0AW)
export EMAIL_SUBJECT_PREFIX=$(get_secret arn:aws:secretsmanager:eu-west-2:339712857727:secret:EMAIL_SUBJECT_PREFIX-9oWLpA)
