FROM nginx:latest

RUN ln -sf /bin/bash /bin/sh

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/

COPY cert.crt /biodb.crt
COPY cert.key /biodb.key
