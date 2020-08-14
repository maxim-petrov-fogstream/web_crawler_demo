# -*- coding: utf-8 -*-

from django.core.management.base import NoArgsCommand

import logging

from tp.models import Catalog
from tp.views import refresh_one_at_a_time

logger = logging.getLogger('django')

class Command(NoArgsCommand):
    help = u'Ебловозит сайт технопоинта'

    def handle_noargs(self, **options):
        logger.info("syncro_cron")
        refresh_one_at_a_time()
