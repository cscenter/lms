ARG FRONTEND_IMAGE=lms-frontend-webpack:latest
ARG BASE_IMAGE=lms-backend-django:latest

FROM ${FRONTEND_IMAGE} as frontend-builder

FROM ${BASE_IMAGE}

# Copy main application code
COPY . /var/www/code/

# Copy frontend assets (webpack bundles + static)
ARG WEBPACK_ENVIRONMENT
ENV WEBPACK_ENVIRONMENT=${WEBPACK_ENVIRONMENT}
ENV WEBPACK_ASSETS_ROOT=/var/www/frontend-code/assets/
COPY --from=frontend-builder /opt/code/assets/ ${WEBPACK_ASSETS_ROOT}

# Compile .mo translation files
ARG DJANGO_STATIC_ROOT=/var/www/static/
ENV DJANGO_STATIC_ROOT=${DJANGO_STATIC_ROOT}
RUN ENV_FILE=/var/www/code/lms/settings/.env.example \
    DJANGO_SETTINGS_MODULE="lms.settings.extended" \
    DJANGO_STATIC_ROOT=${DJANGO_STATIC_ROOT} \
    python manage.py compilemessages

# Call collectstatic (customize the following line with the minimal environment variables needed for manage.py to run):
RUN ENV_FILE=/var/www/code/lms/settings/.env.example \
    DJANGO_SETTINGS_MODULE="lms.settings.extended" \
    DJANGO_STATIC_ROOT=${DJANGO_STATIC_ROOT} \
    python manage.py collectstatic --noinput --ignore "webpack-stats-v*.json"

# Change to a non-root user inside entry point since we write to the /etc/hosts
COPY docker-files/app/docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
