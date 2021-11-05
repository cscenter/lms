ARG BASE_IMAGE=lms-backend-django
FROM ${BASE_IMAGE}

# Install build deps, then run `pip install`,
# then remove unneeded build deps all in a single step.
RUN set -ex \
    && BUILD_DEPS=" \
    build-essential \
    " \
    && apt-get update && apt-get install -y --no-install-recommends $BUILD_DEPS \
    && pip install --no-cache-dir -r /tmp/requirements-dev.txt \
    \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false $BUILD_DEPS \
    && rm -rf /var/lib/apt/lists/*
