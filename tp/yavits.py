# -*- encoding: utf-8

import lxml.html

import datetime

import logging

import traceback

import urllib2
from .parser import Parser

logger = logging.getLogger('django')

class Yavits(Parser):
    def init_category(self, url):
        return [], []

    def parse_categories(self, data):
        return []

    def parse_products(self, data):
        page = lxml.html.document_fromstring(data)
        xs = page.xpath('.//a[contains(concat(" ", normalize-space(@class), " "), " woocommerce-LoopProduct-link ")]')
        result = []
        for x in xs:
            try:
                a = x
                name = a.xpath('.//h2[1]/text()')[0].strip()
                url = a.xpath('@href')[0].strip()
                price = x.xpath(
                    './/*[contains(concat(" ", normalize-space(@class), " "), " amount ")]/text()'
                )
                price = price[0].strip()
                price = filter(lambda y: y.isdigit(), price)
                if price.endswith(u'руб'):
                    price = price[:-3]
                price = int(price)
                product = {
                    "name": name,
                    "tpid": url,
                    "price": price,
                }
                result.append(product)
            except Exception as e:
                pass
        return result

    def next_products_page(self, category, url, i, data):
        page = lxml.html.document_fromstring(data)
        next_page = page.xpath(
            './/*[@class="page-numbers"]'
            '//a[contains(concat(" ", normalize-space(@class), " "), " next ")]/@href'
        )
        if len(next_page) > 0:
            next_page = next_page[0].strip()
            next_page = self.url_unify(next_page)
        else:
            next_page = None
        return next_page

    def parse_root(self, data):
        doc = lxml.html.document_fromstring(data)
        categories = doc.xpath(
            './/ul[@class="product-categories"]//a'
        )
        result = []
        for x in categories:
            try:
                name = x.xpath('./text()')[0].strip()
                url = x.xpath('@href')[0].strip()
                if name and url: result.append([name, url])
            except Exception as e:
                pass
        return result
