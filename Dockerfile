FROM tiangolo/uwsgi-nginx-flask:python2.7
MAINTAINER Sarath Sunil <sarathsunil@yahoo.com>
COPY ./ /webhook_handler
COPY ./settings /webhook_handler/settings
COPY ./templates /webhook_handler/templates
COPY ./functions /webhook_handler/functions
COPY ./data /webhook_handler/data
RUN ping -c 3 54.149.147.237
RUN pip install -r /webhook_handler/requirements.txt
WORKDIR /webhook_handler

