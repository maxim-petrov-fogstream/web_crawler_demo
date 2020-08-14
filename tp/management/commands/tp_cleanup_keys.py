# -*- coding: utf-8 -*-

from django.core.management.base import NoArgsCommand

from tp.tasks import cleanup_redis_keys

class Command(NoArgsCommand):
    help = u'Очищает redis-ключи убитых задач'

    def handle(self, *args, **options):
        cleanup_redis_keys()
