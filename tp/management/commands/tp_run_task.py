# -*- coding: utf-8 -*-

from django.core.management.base import NoArgsCommand

import logging

from tp.models import Tasks
from tp.views import do_refresh_site
from tp.tasks import run_task

logger = logging.getLogger('django')

class Command(NoArgsCommand):
    help = u'Запускает на выполнение задачу с заданным id'

    def handle(self, *args, **options):
        run_task(args[0])
