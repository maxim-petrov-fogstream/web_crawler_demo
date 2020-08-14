# -*- coding: utf-8 -*-
################################################################################

from django.db.models import Q
from django.db import models
from django.conf import settings
import pytz

import lxml.html
import re
import binascii

class Site( models.Model ):
    name = models.CharField(verbose_name=u'Название', max_length=255)
    url = models.URLField(verbose_name=u'Адрес')
    parser = models.CharField(verbose_name=u'Вариант парсера', max_length=255)
    active = models.BooleanField(verbose_name=u'Работает', default=True)
    opts = models.TextField(verbose_name=u'Настройки парсера', blank=True)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = u'Сайт'
        verbose_name_plural = u'Сайты'

################################################################################

class Catalog( models.Model ):
    name    = models.CharField( verbose_name=u'Название', max_length=255)
    url     = models.TextField( verbose_name=u'Адрес' )
    enable  = models.BooleanField( verbose_name=u'Парсить', default=True )
    update  = models.DateTimeField(auto_now=True, editable=False)
    site    = models.ForeignKey(Site, related_name=u'catalogs', verbose_name=u'Сайт')

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = u'Категория'
        verbose_name_plural = u'Категории'
        unique_together = ('site', 'url')

################################################################################

class Product( models.Model ):
    tpid  = models.CharField (
        verbose_name=u'Идетификатор на сайте', max_length=255
    )
    # tpid  = models.IntegerField( verbose_name=u'ID TP', unique=True )
    name  = models.CharField( verbose_name=u'Название', max_length=255 )
    price = models.IntegerField( verbose_name=u'Цена')
    qty   = models.IntegerField( verbose_name=u'Количество' )
    cid   = models.ForeignKey(Catalog, related_name=u'products', verbose_name=u'Категория' )
    sid   = models.ForeignKey(Site, related_name=u'products', verbose_name=u'Сайт')
    request_only = models.BooleanField(verbose_name=u'под заказ', default=False)
    request_line = models.TextField(verbose_name=u'Строка заказа', blank=True, default='')
    second_price = models.IntegerField(verbose_name=u'Вторая цена', null=True)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = u'Товар'
        verbose_name_plural = u'Товары'
        unique_together = ('sid', 'tpid')

################################################################################

class Syncro( models.Model ):
    sku         = models.BigIntegerField( verbose_name=u'SKU', unique=True )
    name        = models.CharField( verbose_name=u'Название', max_length=255 )
    price_opt   = models.IntegerField( verbose_name=u'Цена опт')
    price_inet  = models.IntegerField( verbose_name=u'Цена интернет')
    price_sale  = models.IntegerField( verbose_name=u'Цена розница')
    qty         = models.IntegerField( verbose_name=u'Количество' )

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = u'Товар НК'
        verbose_name_plural = u'Товары НК'

################################################################################

class UtcDateTimeField(models.DateTimeField):
    def from_db_value(self, value, expression, connection, context):
        result = value
        if result is not None:
            result = pytz.utc.localize(result)
            tz = pytz.timezone(settings.TIME_ZONE)
            result = result.astimezone(tz)
        return result

    def get_prep_value(self, value):
        if value is not None:
            value = value.astimezone(pytz.utc)
        return value

class Tasks(models.Model):
    status = models.CharField(u'Состояние', max_length=255, db_column='status')
    source = models.CharField(u'Источник', max_length=255, db_column='source')
    process = models.CharField(
        u'Процесс', blank=True, null=True, max_length=255, db_column='process'
    )
    created = models.DateTimeField(u'Создана', db_column='created')
    started = models.DateTimeField(u'Начало', null=True, db_column='started')
    finished = models.DateTimeField(u'Окончание', null=True, db_column='finished')
    data = models.TextField(u'Исходные данные', db_column='data')
    report = models.TextField(u'Отчёт', null=True, blank=True, db_column='report')

    class Meta:
        verbose_name = u'Задача'
        verbose_name_plural = u'Задачи'
#        managed = False
#        db_table = 'tp_tasks'

    def redis_id(self):
        return 'tp-task-' + str(self.id)
