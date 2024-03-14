#!/bin/bash

conda activate biospecdb

cd repo/biospecdb
git fetch
git checkout origin/main -f

source ./scripts/prd/export_secrets.sh
