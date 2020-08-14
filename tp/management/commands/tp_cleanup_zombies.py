# -*- coding: utf-8 -*-

from django.core.management.base import NoArgsCommand

from tp.tasks import cleanup_zombies

class Command(NoArgsCommand):
    help = u'Убивает зависшие задачи'

    def handle(self, *args, **options):
        cleanup_zombies()
