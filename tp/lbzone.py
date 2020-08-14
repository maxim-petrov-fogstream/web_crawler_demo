# -*- encoding: utf-8

import lxml.html

import logging

import traceback

import urllib2

from .parser import Parser

logger = logging.getLogger('django')

class Lbzone(Parser):
    def init_category(self, url):
        return [], []

    def parse_categories(self, data):
        return []

    def parse_products(self, data):
        page = lxml.html.document_fromstring(data)
        xs = page.xpath('.//div[@class="view-content"]//td[contains(@class, "col-")]')
        result = []
        for x in xs:
            try:
                a = x.xpath('.//*[contains(@class, "views-field-title")]/span/a')[0]
                name = a.xpath('./text()')[0].strip()
                url = a.xpath('@href')[0].strip()
                price = x.xpath(
                    './/*[contains(@class, "views-field-display-price")]/span/text()'
                )
                price = " ".join(price).strip()
                price = price.replace(' ', '')
                if price.endswith(u'руб.'):
                    price = price[:-4]
                price = int(price)
                product = {
                    'name': name,
                    'tpid': url,
                    'price': price,
                }
                result.append(product)
            except Exception as e:
                pass
        return result

    def next_products_page(self, category, url, i, data):
        page = lxml.html.document_fromstring(data)
        next_page = page.xpath(
            './/*[@class="pager"]/li[@class="pager-next"]/a'
        )
        if len(next_page) == 0: return None
        next_page = next_page[0].xpath('@href')[0].strip()
        next_page = self.url_unify(next_page)
        return next_page

    def parse_root(self, data):
        doc = lxml.html.document_fromstring(data)
        categories = doc.xpath(
            './/*[@id="sidebar-left"]//li[contains(@class, "catalog-item-")]/span/a'
        )
        result = []
        for x in categories:
            name = x.xpath('./text()')[0].strip()
            url = x.xpath('@href')[0].strip()
            if name and url: result.append([name, url])
        return result
