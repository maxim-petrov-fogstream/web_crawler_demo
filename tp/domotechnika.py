# -*- encoding: utf-8

import lxml.html
from lxml import etree

import datetime
import time

import logging

import traceback

import cookielib, urllib2
import json
from .parser import Parser

logger = logging.getLogger('django')

hisense = False

class Domotechnika(Parser):


    def __init__(self, site, task):
        super(Domotechnika, self).__init__(site, task)
        if self.opts and 'today_only' in self.opts:
            self.today_only = self.opts['today_only']
        else:
            self.today_only = False
        self.request(site.url)

    def init_category(self, url):
        return [], []

    def parse_categories(self, data):
        return []

    def parse_products(self, data):
        global hisense
        if hisense == False:
            page = lxml.html.document_fromstring(data)
            xs = page.xpath(
                './/*[contains(concat(" ", @class, " "), "product-card__container")]'
                '//*[contains(concat(" ", @class, " "), " product-card col-6 ")]'
            )
            result = []
            for x in xs:
                try:
                    a = x.xpath(
                        './/*[contains(concat(" ", @class, " "), " product-card__title ")]/a')[0]
                    name = "".join(a.xpath('./text()')).strip()
                    url = a.xpath('@href')[0].strip()
                    price = x.xpath(
                        './/*[contains(concat(" ", @class, " "), '
                        '" product-card__price_regular ")]'
                        '/text()'
                    )[0].strip()
                    price = filter(lambda y: y.isdigit(), price)
                    price = int(price)
                    delivery = x.xpath(
                        './/*[@class="lh-1"]//available-btn'
                    )
                    request_only = False
                    request_line = u''
                    if len(delivery) == 0:
                        continue
                    delivery = delivery[0]
                    stores = int(delivery.xpath('@*[name()=":min-stores"]')[0])
                    days = int(delivery.xpath('@*[name()=":min-store-days"]')[0])
                    request_only = not(stores > 0 and days == 0)
                    if days > 0:
                        request_line = u'Через %s дней' % days
                    if stores == 0:
                        continue
                    if self.today_only and request_only:
                        continue

                    product = {
                        "name": name,
                        "tpid": url,
                        "price": price,
                        "request_only": request_only,
                        "request_line": request_line
                    }
                    result.append(product)
                except Exception as e:
                    pass
            return result

        else:
            page = lxml.html.document_fromstring(data)
            xs = page.xpath(
                './/*[contains(concat(" ", @class, " "), "product-card__container")]'
                '//*[contains(concat(" ", @class, " "), " product-card col-6 ")]'
            )
            result = []
            for x in xs:
                try:
                    a = x.xpath(
                        './/*[contains(concat(" ", @class, " "), " product-card__title ")]/a')[0]
                    name = "".join(a.xpath('./text()')).strip()
                    if 'hisense' in name.lower():
                        url = a.xpath('@href')[0].strip()
                        price = x.xpath(
                            './/*[contains(concat(" ", @class, " "), '
                            '" product-card__price_regular ")]'
                            '/text()'
                        )[0].strip()
                        price = filter(lambda y: y.isdigit(), price)
                        price = int(price)
                        delivery = x.xpath(
                            './/*[@class="lh-1"]//available-btn'
                        )
                        request_only = False
                        request_line = u''
                        if len(delivery) == 0:
                            continue
                        delivery = delivery[0]
                        stores = int(delivery.xpath('@*[name()=":min-stores"]')[0])
                        days = int(delivery.xpath('@*[name()=":min-store-days"]')[0])
                        request_only = not (stores > 0 and days == 0)
                        if days > 0:
                            request_line = u'Через %s дней' % days
                        if stores == 0:
                            continue
                        if self.today_only and request_only:
                            continue

                        product = {
                            "name": name,
                            "tpid": url,
                            "price": price,
                            "request_only": request_only,
                            "request_line": request_line
                        }
                        result.append(product)
                except Exception as e:
                    pass
            return result


    def next_products_page(self, category, url, i, data):
        return category.url + ('?page=%s' % (i + 1))

    def load_categories_structure(self, x):
        result = []
        url = x['url']
        name = x['title']
        if name and url: result.append([name, url])
        for y in x['children']:
            result += self.load_categories_structure(y)
        return result

    def root_url(self):
        if 'vladivostok' in self.site.url.lower():
            global hisense
            hisense = True
            return self.site.url + '/api/v1/categories'

        else:
            return self.site.url + '/api/v1/categories'

    def parse_root(self, data):
        categories = json.loads(data)['data']['categories'][1:4]
        result = []
        for x in categories:
            result += self.load_categories_structure(x)
        return result
