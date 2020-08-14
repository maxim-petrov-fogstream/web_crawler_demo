# -*- coding: utf-8 -*-
################################################################################

from django.conf.urls import patterns, include, url
from django.contrib import admin
from tp.urls import tp_urls
admin.autodiscover()
import settings
import django
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

################################################################################

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^tp/', include(tp_urls)),
    (r'^$',  'views.main'),
    (r'^login$',  'views.login'),
    (r'^logout', 'views.logout'),

    (r'^media/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': settings.MEDIA_ROOT,
    }),

    (r'^static/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': settings.STATIC_ROOT,
    }),

)
urlpatterns += staticfiles_urlpatterns()

################################################################################
