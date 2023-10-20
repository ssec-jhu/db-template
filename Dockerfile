FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements/prd.txt /app/requirements.txt

RUN pip3 install -r requirements.txt

COPY manage.py /app/
COPY biospecdb/ /app/biospecdb/
