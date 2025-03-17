import os
from decouple import config
import redis

try:
    # Get the REDIS_URL from the environment variables
    redis_url = config('REDIS_URL')

    if not redis_url:
        raise ValueError("REDIS_URL environment variable is not set.")

    # Connect to Redis using the REDIS_URL
    r = redis.from_url(redis_url)

    r.set('key', 'redis-py')
    value = r.get('key')
    print(f"Redis connection successful. Value: {value.decode('utf-8')}")

except Exception as e:
    print(f"Redis connection failed: {e}")