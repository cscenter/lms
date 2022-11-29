FROM python:3.10-slim-buster AS builder

# Python requirements
COPY Pipfile* /tmp/
RUN pip install --upgrade pip \
    && pip install --no-cache-dir pipenv==2022.11.11 \
    && cd /tmp/ \
    && pipenv --python /usr/local/bin/python requirements > /tmp/requirements-prod.txt \
    && pipenv --python /usr/local/bin/python requirements --dev-only > /tmp/requirements-dev.txt \
    && pip uninstall -y pipenv

FROM python:3.10-slim-buster
LABEL maintainer="webmaster@compscicenter.ru"

# Create a group and user to run our app. Use the same sid/gid
# as nginx container use
ENV APP_USER=appuser
RUN groupadd --gid=101 ${APP_USER} && useradd --no-log-init --uid=101 --gid ${APP_USER} ${APP_USER}

# Install packages needed to run your application (not build deps):
#   libpcre3 -- regular expressions support
#   postgresql-client -- for running database commands
#   git -- some app dependencies (like Hoep) are stored on github
#   gosu -- drop root priviligies in docker-entrypoint.sh
# We need to recreate the /usr/share/man/man{1..8} directories first because
# they were clobbered by a parent image.
RUN set -ex \
    && RUN_DEPS=" \
    libpcre3 \
    gettext \
    git \
    gosu \
    ldap-utils \
    postgresql-client \
    " \
    && seq 1 8 | xargs -I{} mkdir -p /usr/share/man/man{} \
    && apt-get update && apt-get install -y --no-install-recommends $RUN_DEPS \
    && rm -rf /var/lib/apt/lists/*

# Copy in python requirements file
COPY --from=builder /tmp/requirements-*.txt /tmp/

# Install build deps, then run `pip install`,
# then remove unneeded build deps all in a single step.
#   swig, libssl-dev -- dependencies for m2crypto (used by django-ses). XXX: openssl already installed
#   libsasl2-dev python-dev libldap2-dev libssl-dev - python-ldap dependencies
RUN set -ex \
    && BUILD_DEPS=" \
    build-essential \
    libssl-dev \
    swig \
    libpcre3-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    libpng-dev \
    libmagic-dev \
    libgnutls28-dev \
    libldap2-dev \
    libsasl2-dev \
    " \
    && apt-get update && apt-get install -y --no-install-recommends $BUILD_DEPS \
    && pip install --upgrade pip \
    && pip install --no-cache-dir uwsgi==2.0.20 \
    && pip install --no-cache-dir -r /tmp/requirements-prod.txt \
    \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false $BUILD_DEPS \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONIOENCODING="UTF-8"
ENV LC_ALL="C.UTF-8"
ENV LANG="C.UTF-8"
ENV PYTHONUNBUFFERED 1

# Main application code directory
RUN mkdir /var/www && chown ${APP_USER}:${APP_USER} /var/www
RUN mkdir /var/www/code && chown ${APP_USER}:${APP_USER} /var/www/code
WORKDIR /var/www/code/

EXPOSE 8001
