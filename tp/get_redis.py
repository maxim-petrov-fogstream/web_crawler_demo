# -*- coding: utf-8 -*-

from django.conf import settings
import redis

def get_redis():
    host = settings.REDIS_SETTINGS['host']
    port = settings.REDIS_SETTINGS['port']
    return redis.StrictRedis(host=host, port=port, db=0)
