# -*- encoding: utf-8

import lxml.html

import datetime

import logging

import traceback

import urllib2

from .parser import Parser

logger = logging.getLogger('django')

class NK(Parser):
    def init_category(self, url):
        return [], []

    def parse_categories(self, data):
        return []

    def parse_products(self, data):
        page = lxml.html.document_fromstring(data)
        xs = page.xpath('.//*[@id="im_goods_list"]/div')
        result = []
        for x in xs:
            try:
                a = x.xpath('./a[@class="detail"]')[0]
                name = a.xpath('./em/text()')[0].strip()
                url = a.xpath('@href')[0].strip()
                price = x.xpath('./*[@class="cost"]/b/text()')
                price = ' '.join(price)
                price = filter(lambda x: x.isdigit(), price)
                price = int(price)
                price_loyal = x.xpath(
                    './*[contains(concat(" ", @class, " "), " cost_loyalty ")]//text()'
                )
                try:
                    price_loyal = ' '.join(price_loyal)
                    price_loyal = filter(lambda x: x.isdigit(), price_loyal)
                    price_loyal = int(price_loyal)
                except:
                    price_loyal = None
                product = {
                    'name': name,
                    'tpid': url,
                    'price': price,
                    'second_price': price_loyal,
                }
                result.append(product)
            except Exception as e:
                pass
        return result

    def next_products_page(self, category, url, i, data):
        page = lxml.html.document_fromstring(data)
        url = page.xpath(
            '//*[@class="list_navbar--pages"]//*[@class="page_next"]/a/@href'
        )
        if len(url) > 0:
            url = url[0]
            url = self.url_unify(url)
        else:
            url = None
        return url

    def root_url(self):
        return self.site.url + "/im/"

    def parse_root(self, data):
        doc = lxml.html.document_fromstring(data)
        categories = doc.xpath(
            './/div[@id="im_catalogmenu"]/ul/li/.//ul/li/a'
        )
        result = []
        for x in categories:
            name = x.xpath('./text()')[0].strip()
            url = x.xpath('@href')[0].strip()
            if name and url: result.append([name, url])
        return result
