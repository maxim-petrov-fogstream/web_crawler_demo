# -*- coding: utf-8 -*-
################################################################################

from django.conf.urls import patterns, include, url
from django.contrib import admin
admin.autodiscover()
import settings

################################################################################

tp_urls = patterns('tp.views',
    url(r'^$', 'show_sites'),
    url(r'^refresh/(\d+)/$', 'refresh'),

    url(r'^settings/$', 'settings'),
    url(r'^site/$', 'show_sites'),
    url(r'^site/(\d+)/$', 'show_site'),
    url(r'^site/(\d+)/refresh/$', 'refresh_site'),
    url(r'^site/(\d+)/init/$', 'init_site'),
    url(r'^site/(\d+)/settings/$', 'settings_site'),
    url(r'^full-price/(\d+)/$',   'full_price_list'),
    url(r'^category/(\d+)/$',     'show_category'),
    url(r'^category/(\d+)/price/$', 'category_price'),
    url(r'^product/(\d+)/$',      'show_product'),
    url(r'^category/csv/(\d+)/$', 'category_csv'),
    #url(r'^init/$', 'init_view'),
    url(r'^tasks/$', 'show_tasks'),
    url(r'^tasks/archive/$', 'show_old_tasks'),
    url(r'^tasks/start/$', 'start_task'),
    url(r'^tasks/stop/$', 'stop_task'),
    url(r'^task/(\d+)/$', 'show_task'),
    url(r'^tasks/restart-errors/$', 'retry_error_categories'),
)

################################################################################
