# -*- encoding: utf-8

import lxml.html
from lxml import etree

import datetime

import logging

import traceback
from .parser import Parser
import urllib
import json

logger = logging.getLogger('django')

class VLazer(Parser):
    def init_category(self, url):
        return [], []

    def parse_categories(self, data):
        return []

    def parse_products(self, data):
        page = lxml.html.document_fromstring(data)
        xs = page.xpath
        xs = page.xpath(
            './/*[contains(@class, "catalog")]'
            '//*[contains(@class, "cellview")]'
            '/*[contains(@class, "cell")]'
        )
        jp = page.xpath(
            './/*[contains(@class, "jp_offset")]/text()'
        )
        jp = jp[0]
        jp = urllib.urlencode({ 'offset': jp })
        jp_url = self.site.url + '/catalog/~/offset'
        jp = self.request(jp_url, jp,
                          {'X-Requested-With': 'XMLHttpRequest',
                           'Accept': '*/*'})
        jp = json.loads(jp)
        jp = jp['offset']
        jp = int(jp)
        result = []
        for x in xs:
            try:
                a = x.xpath('./*[@class="name"]/a')[0]
                name = "".join(a.xpath('./text()')).strip()
                url = a.xpath('@href')[0].strip()
                price = x.xpath(
                    u'./*[contains(@class, "price")]'
                    u'/li'
                )
                price = "".join(price[0].xpath('./text()'))
                price = filter(lambda y: y.isdigit(), price)
                price = int(price) - jp
                delivery = x.xpath(
                    './*[@class="availablelist"]/a/span/text()'
                )
                delivery = filter(lambda y: not y.isspace(), delivery)
                if delivery == 'Доступенсегодня':
                    request_only = False
                else:
                    request_only = True
                product = {
                    'name': name,
                    'tpid': url,
                    'price': price,
                    'request_only': request_only,
                }
                result.append(product)
            except Exception as e:
                pass
        return result

    def next_products_page(self, category, url, i, data):
        page = lxml.html.document_fromstring(data)
        next_page = page.xpath(
            './/*[contains(@class, "pageline")]/ul/li/a'
        )
        next_page = filter(lambda x: "".join(x.xpath('./text()')).strip() == u'Следующая', next_page)
        if len(next_page) > 0:
            next_page = self.site.url + next_page[0].xpath('@href')[0].strip()
        else:
            next_page = None
        return next_page

    def parse_root(self, data):
        doc = lxml.html.document_fromstring(data)
        categories = doc.xpath(
            './/*[contains(@class, "catmenu_container")]'
            '//a[contains(@class, "element")]'
        )
        result = []
        for x in categories:
            a = x
            name = "".join(a.xpath('./text()')).strip()
            url = "".join(a.xpath('@href')).strip()
            if name and url: result.append([name, url])
        return result
