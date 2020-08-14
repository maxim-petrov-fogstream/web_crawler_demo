# -*- encoding: utf-8

import lxml.html
from lxml import etree

import datetime
import time

import logging

import traceback

import json
import urllib
from urlparse import urlparse
from .parser import Parser

logger = logging.getLogger('django')

class MagazinDV(Parser):
    def init_category(self, url):
        return [], []

    def parse_categories(self, data):
        return []

    def parse_products(self, data):
        page = lxml.html.document_fromstring(data)
        xs = page.xpath(
            './/*[@id="mfilter-content-container"]//'
            '*[contains(concat(" ", @class, " "), " product-layout ")]'
        )
        result = []
        for x in xs:
            try:
                a = x.xpath('.//*[contains(concat(" ", @class, " "), " name ")]/a')[0]
                name = "".join(a.xpath('./text()')).strip()
                url = a.xpath('@href')[0].strip()
                price = x.xpath(
                    './/*[contains(concat(" ", @class, " "), " price ")]/text()'
                )
                price = price[0].strip()
                price = filter(lambda y: y.isdigit(), price)
                price = int(price)
                buy_button = x.xpath(
                    './/*[contains(concat(" ", @class, " "), " btn-addtocart ")]'
                )
                if len(buy_button) == 0:
                    raise Exception('Нет цены')
                product = {
                    "name": name,
                    "tpid": url,
                    "price": price,
                    "request_only": False
                }
                result.append(product)
            except Exception as e:
                pass
        return result

    def next_products_page(self, category, url, i, data):
        page = lxml.html.document_fromstring(data)
        next_page = page.xpath(
            './/*[contains(concat(" ", normalize-space(@class), " "), " pagination ")]'
            '/li/a[text()=">"]'
        )
        if len(next_page) > 0:
            next_page = next_page[0].xpath('@href')[0].strip()
            next_page = self.url_unify(next_page)
        else:
            next_page = None
        return next_page


    def parse_root(self, data):
        doc = lxml.html.document_fromstring(data)
        categories = doc.xpath(
            './/*[@id="menu-list"]//*[@class="h5"]/a'
        )
        print len(categories)
        result = []
        for x in categories:
            name = "".join(x.xpath('./text()')).strip()
            url = "".join(x.xpath('@href')).strip()
            if name and url: result.append([name, url])
        return result
