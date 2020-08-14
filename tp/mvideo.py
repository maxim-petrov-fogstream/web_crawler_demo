# -*- encoding: utf-8

import lxml.html

import datetime
import time

import logging

import traceback

import urllib, urllib2, cookielib
import json
from .parser import Parser

logger = logging.getLogger('django')

conc_url = False

class MVideo(Parser):
    user_agent = (
        'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
    )
    max_pages = 100
    def init_category(self, url):
        return [], []

    def parse_categories(self, data):
        return []

    def parse_products_old(self, xs):
        result = []
        for x in xs:
            try:
                a = x.xpath('.//*[@class="product-tile-title"]/a')[0]
                name = "".join(a.xpath('./text()')).strip()
                url = "".join(a.xpath('@href')).strip()
                price = x.xpath(
                    './/*[contains(concat(" ", normalize-space(@class), " "), " product-price-current ")]'
                    '/text()'
                )
                price = "".join(price)
                price = filter(lambda y: y.isdigit(), price)
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


    def parse_products_c(self, xs):
        result = []
        for x in xs:
            try:
                a = x.xpath('.//*[@class="c-product-tile__description"]//h4/a')[0]
                name = "".join(a.xpath('./text()')).strip()
                url = "".join(a.xpath('@href')).strip()
                price = x.xpath(
                    './/*[contains(concat(" ", normalize-space(@class), " "), " c-pdp-price__current ")]'
                    '/text()'
                )
                price = "".join(price)
                price = filter(lambda y: y.isdigit(), price)
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


    def parse_products(self, data):
        page = lxml.html.document_fromstring(data)

        ds = page.xpath(
            './/*[contains(concat(" ", normalize-space(@class), " "), '
            '" c-plp-facets__item-link sel-facet-name u-mr-4 c-checkbox__text ")]'
        )

        if len(ds) > 0:
            global conc_url
            conc_url=True
        else:
            conc_url=False

        xs = page.xpath(
            './/*[contains(concat(" ", normalize-space(@class), " "), " c-product-tile ")]'
        )
        ys = page.xpath(
            './/*[contains(concat(" ", normalize-space(@class), " "), " product-tile ")]'
        )
        if len(xs) > 0:
            return self.parse_products_c(xs)
        elif len(ys) > 0:
            return self.parse_products_old(ys)
        else:
            return []

    def next_products_page(self, category, url, i, data):
        page = lxml.html.document_fromstring(data)
        next_page = page.xpath(
            './/*[contains(concat(" ", normalize-space(@class), " "), " c-pagination ")]'
            '//*[contains(concat(" ", normalize-space(@class), " "), " c-pagination__next ")]'
            '/@href'
        )
        if len(next_page) == 0:
            next_page = page.xpath(
                './/*[contains(concat(" ", normalize-space(@class), " "), " pagination ")]'
                '//*[contains(concat(" ", normalize-space(@class), " "), " ico-pagination-next ")]'
                '/@href'
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
            './/*[@class="header-nav-drop-down-list-item"]/a'
        )
        result = []
        for x in categories:
            a = x
            name = "".join(a.xpath('./text()')).strip()
            url = "".join(a.xpath('@href')).strip()
            if name and url: result.append([name, url])
        return result
