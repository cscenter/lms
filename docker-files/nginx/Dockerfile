FROM nginx:1.21-alpine
LABEL maintainer="sergey.zherevchuk@jetbrains.com"

RUN rm /etc/nginx/conf.d/default.conf
COPY ./conf.d/default.conf /etc/nginx/conf.d/
COPY ./conf.d/*.template /etc/nginx/templates/

EXPOSE 80

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]


CMD ["nginx", "-g", "daemon off;"]
