FROM tiangolo/uwsgi-nginx-flask:python2.7
MAINTAINER Sarath Sunil <sarathsunil@yahoo.com>
COPY ./ /webhook_handler
COPY ./settings /webhook_handler/settings
COPY ./templates /webhook_handler/templates
COPY ./functions /webhook_handler/functions
COPY ./data /webhook_handler/data
RUN ping -c 3 54.149.147.237
RUN apt-get update && apt-get -y install sudo
RUN sudo apt-get -y  --fix-missing update
RUN sudo apt-get -y  --fix-missing upgrade
RUN apt-get install --fix-missing -y xvfb
RUN apt-get install --fix-missing -y  wkhtmltopdf
RUN pip install -r /webhook_handler/requirements.txt
WORKDIR /webhook_handler

