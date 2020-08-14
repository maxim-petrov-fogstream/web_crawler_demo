# -*- encoding: utf-8

import lxml.html
from lxml import etree

import datetime
import time

import logging

import traceback

import cookielib, urllib2
from .parser import Parser

logger = logging.getLogger('django')


class KB(Parser):
    def parse_products(self, data):
        page = lxml.html.document_fromstring(data)
        xs = page.xpath(
            './/*[contains(concat(" ", @class, " "), " products_wrap ")]'
            '//*[contains(concat(" ", @class, " "), " product ")]'
        )
        result = []
        for x in xs:
            try:
                a = x.xpath('.//*[@class="name"]')[0]
                name = "".join(a.xpath('./text()')).strip()
                url = a.xpath('@href')[0].strip()
                price = x.xpath(
                    './/*[@class="price"]/*[@class="amount"]'
                )
                price = "".join(price[0].xpath('./text()'))
                price = filter(lambda y: y.isdigit(), price)
                price = int(price)
                request_only = False
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
            './/*[contains(concat(" ", @class, " "), "pagination_wrap")]'
            '//a[@class="next_page"]/@href'
        )
        if len(next_page) > 0 and next_page[0] != 'javascript:void(0);':
            next_page = self.site.url + next_page[0]
        else:
            next_page = None
        return next_page

    def root_url(self):
        return self.site.url + "/catalog/"

    def parse_categories(self, data):
        doc = lxml.html.document_fromstring(data)
        categories = doc.xpath(
            './/a[@class="category_title_link"]'
        )
        result = []
        for a in categories:
            name = "".join(a.xpath('.//*[@class="title"]/text()')).strip()
            url = "".join(a.xpath('@href')).strip()
            if name and url: result.append([name, url])
        print result
        return result
