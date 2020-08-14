# -*- coding: utf-8 -*-

from django.core.management.base import NoArgsCommand

import logging

from tp.models import Site
from tp.tasks import update_site_task

logger = logging.getLogger('django')

class Command(NoArgsCommand):
    help = u'Обновляет сайт с заданным id'

    def handle(self, *args, **options):
        site = Site.objects.get(id=args[0])
        update_site_task(site, 'cron')

