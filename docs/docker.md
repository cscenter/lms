### docker-compose.yml

```bash
docker volume create --name postgres-data
docker volume create --name lms-media
docker volume create --name lms-redis-data
# Recreate
docker-compose down -v
docker-compose build django django-tests
docker-compose up -d django
```


### Debug container

```bash
docker exec -it <image> /bin/bash
docker run --rm -it --entrypoint=/bin/bash <image>
```
