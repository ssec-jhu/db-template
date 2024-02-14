FROM nginx:latest

RUN ln -sf /bin/bash /bin/sh

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/

COPY cert.crt /biospecdb.crt
COPY cert.key /biospecdb.key
