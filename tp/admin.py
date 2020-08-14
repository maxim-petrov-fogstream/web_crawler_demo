# -*- coding: utf-8 -*-
################################################################################

from django.contrib import admin
from tp.models import *


class CatalogAdmin( admin.ModelAdmin ): 
    list_display = ('name', 'url', 'enable', 'update',)
    search_fields = ('name', 'url', 'enable', 'update',)
    list_filter = ('enable', 'update',)
admin.site.register(Catalog,CatalogAdmin)


class ProductAdmin( admin.ModelAdmin ): 
    list_display = ('tpid', 'name', 'price', 'qty',)
    search_fields = ('tpid', 'name', 'price', 'qty',)
admin.site.register(Product,ProductAdmin)


class SyncroAdmin( admin.ModelAdmin ): 
    list_display = ('sku', 'name', 'price_opt', 'price_sale', 'qty',)
    search_fields = ('sku', 'name', 'price_opt', 'price_sale', 'qty',)
admin.site.register(Syncro,SyncroAdmin)


class SiteAdmin( admin.ModelAdmin ):
    list_display = ('name', 'url', 'parser', 'active', 'opts',)
admin.site.register(Site,SiteAdmin)


