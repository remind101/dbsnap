FROM phusion/baseimage:0.10.0
MAINTAINER Michael Barrett <mike@remind101.com>

WORKDIR /src

RUN apt-get update && apt-get install -y python python-setuptools

COPY . /src

RUN cd /src; python setup.py install

RUN mkdir -p /etc/my_init.d; cp /src/build_cron.sh /etc/my_init.d/build_cron.sh
