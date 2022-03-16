FROM nginx:1.21-alpine
LABEL maintainer="webmaster@compscicenter.ru"

COPY ./nginx.conf /etc/nginx/nginx.conf
COPY ./site.conf /etc/nginx/conf.d/site.conf

# Default nginx entrypoint scripts need root privileges, remove them
RUN rm /docker-entrypoint.d/10-listen-on-ipv6-by-default.sh
RUN rm /docker-entrypoint.d/20-envsubst-on-templates.sh

EXPOSE 8080
