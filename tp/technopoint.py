# -*- encoding: utf-8

import lxml.html

import datetime
import time

import logging

import traceback

import urllib, urllib2, cookielib
import json
import re
from urlparse import urlparse
from .parser import Parser
import js2py
import os
import subprocess
import tempfile

logger = logging.getLogger('django')

class Technopoint(Parser):
    max_pages = 100
    js_base = """
var location = {href: ""};
var navigator = {
    appCodeName: "Mozilla"
  , appName: "Netscape"
  , appVersion: "5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"
  , cookieEnabled: true
  , geolocation: undefined
    /*
      clearWatch
      getCurrentPosition
      watchPosition
    */
  , mimeTypes: []
    /*
    */
  , onLine: true
  , platform: "MacIntel"
  , plugins: []
    /*
    */
  , product: "Gecko"
  , productSub: "20030107"
  , usegAgent: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"
  , vendor: "Joyent"
  , vendorSub: ""
};
    """

    def cookie_redirect(self, data):
        if re.search(r'location.href=ipp.makeUrl', data) is None: return None
        key = re.search(r'decrypt\.setPrivateKey\("([^"]+)"\)', data)
        if key is None:
            base = re.search(r'location.href=ipp.makeUrl\("([^"]+)"\)', data).group(1)
            query = re.search(r'url \+= ([^;]+);', data).group(1)
            parts = re.findall(r'"([^"]+)"', query)
            return base + ''.join(parts)
        key = key.group(1)
        msg = re.search(r'return decrypt\.decrypt\("([^"]+)"\)', data).group(1)
        p = subprocess.Popen(
            ['base64', '--decode'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        p.stdin.write(msg)
        p.stdin.close()
        msg = p.stdout.read()
        p.stdout.close()
        p.wait()
        key = "-----BEGIN RSA PRIVATE KEY-----\n" + key + "\n-----END RSA PRIVATE KEY-----"
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(key)
        f.close()
        p = subprocess.Popen(
            ['openssl', 'rsautl', '-decrypt', '-inkey', f.name],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        p.stdin.write(msg)
        p.stdin.close()
        arg = p.stdout.read()
        p.stdout.close()
        p.wait()
        os.unlink(f.name)
        data = re.sub(
            r'var decrypt = new JSEncrypt\(\)', '', data
        )
        data = re.sub(
            r'decrypt\.setPrivateKey\("([^"]+)"\)',
            '',
            data
        )
        data = re.sub(
            r'return decrypt\.decrypt\("([^"]+)"\)',
            'return "' + arg + '"',
            data
        )
        page = lxml.html.document_fromstring(data)
        js = page.xpath('.//script/text()')[0]
        start = re.search(r'var ipp =', js).span()[0]
        js = js[start:]
        js = self.js_base + js + ";location.href"
        url = js2py.eval_js(js)
        return url

    def request(self, url, data=None, headers = {}):
        headers['X-Requested-With'] = 'XMLHttpRequest'
        data = super(Technopoint, self).request(url, data, headers)
        redirect = self.cookie_redirect(data)
        if not (redirect is None):
            super(Technopoint, self).request(redirect)
            return super(Technopoint, self).request(url, data, headers)
        else:
            return data

    def __init__(self, site, task):
        super(Technopoint, self).__init__(site, task)
        self.request(site.url)
        city = self.opts['city']
        self.request(site.url + '/ajax/change-city/?city_guid=' + city)

    def do_request(self, url, data=None, headers = {}):
        try:
            for x in self.cookiejar:
                if x.name == 'catalog-filter-extended-features':
                    self.cookiejar.clear(x.domain, x.path, x.name)
        except Exception as e:
            pass
        return super(Technopoint, self).do_request(url, data, headers)

    def init_category(self, url):
        return [], []

    def parse_categories(self, data):
        page = lxml.html.document_fromstring(data)
        xs = page.xpath(
            './/*[@class="category-item-desktop"]'
        )
        result = []
        for x in xs:
            try:
                name = "".join(x.xpath('.//*[@class="category-title"]/text()')).strip()
                url = "".join(x.xpath('@href')).strip()
                if name and url: result.append([name, url])
            except Exception as e:
                pass
        return result

    def load_product_page(self, path, i):
        url = self.url_unify(path)
        q = urllib.urlencode({
            'order': 3,
            'stock': 2,
            'p': i,
        })
        if url.find('?') == -1:
            url += '?'
        else :
            url += '&'
        url += q
        data = json.loads(self.request(
            url, None, {
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': self.url_unify(path),
            }
        ))
        return data

    def find_ajax_url(self, data):
        page = lxml.html.document_fromstring(data)
        x = page.xpath(
            './/*[@class="page-products"]'
        )
        if len(x) == 0: return None
        x = x[0]
        url = x.xpath("@data-get-catalog-items-url")
        if len(url) == 0: return None
        url = self.url_unify(url[0].strip())
        params = x.xpath("@data-virtual-category-params")
        if len(params) == 0: return url
        params = params[0]
        params = params.strip()
        if len(params) == 0: return url
        params = "var x = " + params
        params = js2py.eval_js(params)
        s = {}
        for i in params:
            if type(i) is unicode:
                if type(params[i]) is js2py.base.JsObjectWrapper:
                    for j in params[i]:
                        s[i + '[' + j + ']'] = params[i][j]
        s = urllib.urlencode(s)
        if len(s) == 0: return url
        url += '&' + s
        return url

    def update_products(self, category, data):
        base = category.url
        products = self.parse_products(data)
        path = self.find_ajax_url(data)
        if path is None: return
        i = 0
        while i <= self.max_pages and len(products) > 0:
            i += 1
            data = self.load_product_page(path, i)
            if data['html'].strip() == "": break
            products = self.parse_products(data['html'])
            self.update_products_base(category, products)
            if not data['data']['hasNextPage']: break

    def parse_products(self, data):
        page = lxml.html.document_fromstring(data)
        xs = page.xpath(
            './/*[contains(concat(" ", @class, " "), " catalog-product ")]'
        )
        result = []
        for x in xs:
            try:
                a = x.xpath('.//*[@class="title"]/a')[0]
                name = "".join(a.xpath('./h3/text()')).strip()
                url = "".join(a.xpath('@href')).strip()
                price = x.xpath(
                    './/*[@class="product-price"]'
                    '//*[@class="price_g"]'
                    '/span[@data-of="price-total"]/text()'
                )
                price = "".join(price)
                price = filter(lambda y: y.isdigit(), price)
                price = int(price)
                request_only = False
                request_line = ''
                avail = x.xpath(
                    './/*[contains(concat(" ", @class, " "), " order-avail-wrap ")]'
                    '//*[@class="available"]'
                )
                request_preline = "".join(x.xpath(
                    './/*[contains(concat(" ", @class, " "), " avail-text ")]'
                    '/*[contains(concat(" ", @class, " "), " available ")]/text()'
                )).strip()
                request_line = "".join(x.xpath(
                    './/*[contains(concat(" ", @class, " "), " avail-text ")]'
                    '/*[contains(concat(" ", @class, " "), " pseudo-link ")]/span/text()'
                )).strip()
                if request_preline.startswith(u'В наличии') or request_line == u'сегодня':
                    request_only = False
                    request_line = ''
                else:
                    request_only = True
                product = {
                    "name": name,
                    "tpid": url,
                    "price": price,
                    "request_only": request_only,
                    "request_line": request_line,
                }
                result.append(product)
            except Exception as e:
                pass
        return result

    def parse_root(self, data):
        doc = lxml.html.document_fromstring(data)
        categories = doc.xpath(
            './/a[@class="catalog-icon"]'
        )
        result = []
        for x in categories:
            name = "".join(x.xpath('./span[@class="title"]/text()')).strip()
            url = "".join(x.xpath('@href')).strip()
            if name and url: result.append([name, url])
        return result
