# Base redis
FROM redis:6.2-bullseye
# Copy custom redis.conf, which includes 'loadmodule /rejson/librejson.so'
COPY redis.conf /usr/local/etc/redis/redis.conf
COPY librejson.so /rejson/librejson.so
CMD [ "redis-server", "/usr/local/etc/redis/redis.conf" ]