# -*- encoding: utf-8

import lxml.html
from lxml import etree

import datetime
import time

import logging

import traceback

import urllib
from urlparse import urlparse
from .parser import Parser

logger = logging.getLogger('django')


class Eldorado(Parser):
    def update_category_url(self, category):
        p = urlparse(category.url)
        url = ''
        if p.scheme:
            url += p.scheme + '://'
        else:
            url += 'http://'
        url += p.netloc + p.path
        if p.query:
            url += '?' + p.query + '&list_num=36'
        else:
            url += '?list_num=36'
        return url

    def update_products(self, category, data):
        url = self.update_category_url(category)
        i = 1
        products_base = self.parse_products(data)
        products = products_base
        self.update_products_base(category, products)
        url = self.next_products_page(category, url, i, data)
        while url and i <= self.max_pages and len(products_base) > 0:
            i += 1
            data = self.request(url)
            products_base = self.parse_products(data)
            products = products_base
            self.update_products_base(category, products)
            url = self.next_products_page(category, url, i, data)


    def parse_products(self, data):
        parser = lxml.html.HTMLParser(recover=True)
        page = etree.fromstring(data, parser)
        xs = page.xpath(
            './/*[contains(concat(" ", @class, " "), " goodsList ")]'
            '//*[contains(concat(" ", @class, " "), " item ")]'
        )
        result = []
        for x in xs:
            try:
                sample = x.xpath(
                    './/*[contains(concat(" ", @class, " "), " shield-circle-vitrina ")]'
                )
                if len(sample) != 0:
                    continue

                product_id = x.xpath(
                    './/*[contains(concat(" ", @class, " "), " cartButton ")]/@data-bid'
                )
                if len(product_id) > 0:
                    product_id = product_id[0]
                else:
                    product_id = None
                a = x.xpath('.//*[@class="itemTitle"]/a')[0]
                name = "".join(a.xpath('./text()')).strip()
                url = a.xpath('@href')[0].strip()
                price = x.xpath(
                    './/*[@class="priceContainer"]'
                    '//*[contains(concat(" ", @class, " "), " itemPrice ")]')
                price = "".join(price[0].xpath('./text()'))
                price = filter(lambda y: y.isdigit(), price)
                price = int(price)
                delivery = x.xpath(
                    './/*[contains(concat(" ", @class, " "), "delivery-details")]/p'
                )
                avail = False
                for d in delivery:
                    d = "".join(d.xpath('.//text()'))
                    d = filter(lambda y: not y.isspace(), d)
                    d = d.encode('utf-8')
                    if 'сегодня' in d.lower() or 'завтра' in d.lower():
                        avail = True
                        break
                if not avail: continue
                product = {
                    "product_id": product_id,
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
            './/*[contains(@class, "pager")]'
            '//*[contains(@class, "buttonNext")]'
        )
        if len(next_page) > 0:
            next_page = next_page[0].xpath('@href')[0].strip()
            next_page = self.url_unify(next_page)
        else:
            next_page = None
        return next_page

    def parse_categories(self, data):
        parser = lxml.html.HTMLParser(recover=True)
        doc = etree.fromstring(data, parser)
        subcats = doc.xpath(
            './/*[contains(concat(" ", @class, " "), " new-catalog-block__link ")]'
        )
        result = []
        for el in subcats:
            name = "".join(el.xpath('./text()')).strip()
            url = "".join(el.xpath('@href')).strip()
            if name and url:
                result.append([name, url])
        return result

    def parse_root(self, data):
        parser = lxml.html.HTMLParser(recover=True)
        doc = etree.fromstring(data, parser)
        categories = doc.xpath(
            './/a[contains(concat(" ", @class, " "), " headerCatalogAllItem ")]'
        )
        result = []
        for x in categories:
            name = "".join(x.xpath(
                './*[@class="headerCatalogAllItem-name"]/text()'
            )).strip()
            url = "".join(x.xpath('@href')).strip()
            if name and url: result.append([name, url])
        return result