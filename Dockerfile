FROM python:3
WORKDIR /opt/nomad/
RUN apt-get update
RUN apt-get -y install \
  libpq-dev postgresql-client \
  postgresql-client-common \
  binutils libproj-dev \
  gdal-bin python-gdal \
  && apt-get clean \
  && apt-get autoremove
RUN pip install -U pip
ADD requirements.txt .
RUN pip install -U -r requirements.txt
ADD . .
EXPOSE 5000
