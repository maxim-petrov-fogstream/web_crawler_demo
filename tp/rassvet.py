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

class Rassvet(Parser):
    def init_category(self, url):
        return [], []

    def parse_categories(self, data):
        return []

    def parse_products(self, data):
        page = lxml.html.document_fromstring(data)
        xs = page.xpath(
            './/*[contains(concat(" ", @class, " "), " type-product ")]'
        )
        result = []
        for x in xs:
            try:
                a = x.xpath('.//*[@class="product-title"]/a')[0]
                name = "".join(a.xpath('./text()')).strip()
                url = a.xpath('@href')[0].strip()
                price = x.xpath('.//*[contains(concat(" ", @class, " "), " amount ")]/text()')[0].strip()
                price = filter(lambda y: y.isdigit(), price)
                price = price[:-2]
                price = int(price)
                product = {
                    "name": name,
                    "tpid": url,
                    "price": price,
                    "request_only": False,
                }
                result.append(product)
            except Exception as e:
                pass
        return result

    def next_products_page(self, category, url, i, data):
        page = lxml.html.document_fromstring(data)
        next_page = page.xpath(
            './/*[contains(concat(" ", normalize-space(@class), " "), " woocommerce-pagination ")]'
            '//a[contains(concat(" ", normalize-space(@class), " "), " next ")]'
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
            './/*[@class="menu-categories-column"]//a'
        )
        result = []
        for x in categories:
            a = x
            name = "".join(a.xpath('./text()')).strip()
            url = "".join(a.xpath('@href')).strip()
            if name and url: result.append([name, url])
        return result
