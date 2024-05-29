FROM python:3.11

RUN ln -sf /bin/bash /bin/sh

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements/prd.txt /app/requirements.txt

RUN pip3 install -r requirements.txt

COPY manage.py /app/
COPY biodb/ /app/biodb/
COPY config/ /app/config/

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
