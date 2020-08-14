# -*- encoding: utf-8

import lxml.html

import datetime
import time

from django.db.models import Q
from django.db.utils import IntegrityError
from django.shortcuts import render

from constance import config

from tp.models import *

import logging

import traceback

import urllib, urllib2, cookielib
from StringIO import StringIO
import gzip
import json
import re
import pytz
import random

from tp.get_redis import get_redis

logger = logging.getLogger('django')

class ParserSkipError(Exception): pass

class ParserErrorLimit(Exception): pass

class Parser(object):
    user_agent = (
        'Mozilla/5.0 (X11; Linux x86_64) ' +
        'AppleWebKit/537.36 (KHTML, like Gecko) ' +
        'Chrome/57.0.2987.98 Safari/537.36'
    )
    max_pages = 50
    max_last_items = 10
    max_errors = 200

    def __init__(self, site, task):
        self.site = site
        self.task = task
        if site.opts:
            self.opts = json.loads(site.opts)
        else:
            self.opts = {}
        self.cookiejar = cookielib.CookieJar()
        self.cookies = urllib2.HTTPCookieProcessor(self.cookiejar)
        self.http_proxy = None
        self.https_proxy = None
        if self.opts and 'http_proxy' in self.opts:
            self.http_proxy = str(self.opts['http_proxy'])
            self.https_proxy = str(self.opts['http_proxy'])
        elif self.opts and 'https_proxy' in self.opts:
            self.http_proxy = str(self.opts['https_proxy'])
            self.https_proxy = str(self.opts['https_proxy'])
        if self.opts and 'cookies' in self.opts:
            for key, value in self.opts['cookies'].iteritems():
                self.cookiejar.set_cookie(self.simple_cookie(key, value))
        self.last_time = time.time()
        self.redis = get_redis()
        self.state = {
            'requests': 0,
            'request_errors': 0,
            'bytes_transferred': 0,
            'raw_categories': 0,
            'raw_products': 0,
            'real_categories': 0,
            'real_products': 0,
            'last_activity': self.now(),
            'last_requests': [],
            'last_errors': [],
            'total_errors': 0,
            'error_categories': []
        }
        self.categories = {}
        self.publish_state()

    def now(self):
        t = pytz.datetime.datetime.now()
        t = t.strftime("%Y-%m-%d %H:%M:%S")
        return t

    def publish_state(self):
        self.state['last_activity'] = self.now()
        s = json.dumps(self.state)
        name = self.task.redis_id()
        self.redis.set(name, s)

    def simple_cookie(self, name, value):
        domain = self.site.url
        domain = re.sub(r'^https?://', '', domain)
        ck = cookielib.Cookie(
            version=0, name=name, value=value,
            port=None, port_specified=False, domain=domain,
            domain_specified=False, domain_initial_dot=False,
            path='/', path_specified=True, secure=False, expires=None,
            discard=True, comment=None, comment_url=None,
            rest={'HttpOnly': None}, rfc2109=False
        )
        return ck

    def throttle(self):
        if self.opts and 'rpm' in self.opts and self.opts['rpm'] > 0:
            delay = 60.0 / self.opts['rpm']
            diff = time.time() - self.last_time
            if diff < 0: diff = 0
            if diff < delay:
                s = delay - diff
                if s < 0: s = 0
                time.sleep(s)
            self.last_time = time.time()

    def do_request(self, url, data=None, headers = {}):
        self.throttle()
        if self.user_agent: headers['User-Agent'] = self.user_agent
        headers['Accept-Encoding'] = 'gzip'
        request = urllib2.Request(url, headers=headers)
        proxy = {}
        if self.http_proxy: proxy['http'] = self.http_proxy
        if self.https_proxy: proxy['https'] = self.https_proxy
        proxy = urllib2.ProxyHandler(proxy)
        opener = urllib2.build_opener(proxy, self.cookies)
        response = opener.open(request, data, 30)
        data = response.read()
        self.state['bytes_transferred'] += len(data)
        if response.info().getheader('Content-encoding') == 'gzip':
            buf = StringIO(data)
            f = gzip.GzipFile(fileobj=buf)
            data = f.read()
        return data

    def add_error(self, short, now, info):
        if self.state['total_errors'] >= self.max_errors:
            raise ParserErrorLimit
        self.state['total_errors'] += 1
        errs = self.state['last_errors']
        if len(errs) >= self.max_last_items:
            errs.pop(0)
        logger.info(info)
        errs.append({
            'time': now,
            'short': short,
            'info': info,
        })

    def add_request(self, url, now, result):
        reqs = self.state['last_requests']
        if len(reqs) >= self.max_last_items:
            reqs.pop(0)
        reqs.append({
            'time': now,
            'url': url,
            'result': result,
        })

    def request(self, url, data=None, headers = {}):
        try:
            self.state['requests'] += 1
            data = self.do_request(url, data, headers)
            now = self.now()
            self.add_request(url, now, 'success')
            self.publish_state()
            return data
        except Exception as e:
            self.state['request_errors'] += 1
            now = self.now()
            self.add_request(url, now, 'error')
            self.add_error(u'Не удалось загрузить страницу %s' % url,
                           now, traceback.format_exc())
            self.publish_state()
            raise ParserSkipError

    def url_unify(self, url):
        if not re.match(r'^https?://', url): url = self.site.url + url
        return url

    def init_base(self, categories):
        names = []
        urls = []
        for [name, url] in categories:
            try:
                url = self.url_unify(url)
                if url in self.categories: continue
                self.state['raw_categories'] += 1
                category, created = Catalog.objects.get_or_create(site=self.site, url=url)
                category.name = name
                category.save()
                names.append(name)
                urls.append(url)
                ns, us = self.init_category(url)
                names += ns
                urls += us
                self.categories[url] = True
            except ParserSkipError as e:
                pass
            except ParserErrorLimit as e:
                raise e
            except Exception as e:
                now = self.now()
                self.add_error(u'Не удалось обновить категорию "%s" (%s)' % (name, url),
                               now, traceback.format_exc())
        return [names, urls]

    def init_category(self, url):
        doc = self.request(url)
        categories = self.parse_categories(doc)
        return self.init_base(categories)

    def init_site(self):
        url = self.root_url()
        doc = self.request(url)
        categories = self.parse_root(doc)
        names, urls = self.init_base(categories)
        Catalog.objects.filter(site=self.site).exclude(url__in=urls).delete()
        return [names, urls]

    def update_base(self, categories):
        names = []
        urls = []
        for [name, url] in categories:
            try:
                url = self.url_unify(url)
                if url in self.categories: continue
                self.state['raw_categories'] += 1
                category, created = Catalog.objects.get_or_create(site=self.site, url=url)
                category.name = name
                category.save()
                names.append(name)
                urls.append(url)
                ns, us = self.update_category(category)
                names += ns
                urls += us
                self.categories[url] = True
            except ParserSkipError as e:
                self.state['error_categories'].append([name, url])
            except ParserErrorLimit as e:
                raise e
            except Exception as e:
                now = self.now()
                self.add_error(u'Не удалось обновить категорию "%s" (%s)' % (name, url),
                               now, traceback.format_exc())
                self.state['error_categories'].append([name, url])
        return [names, urls]

    def update_products_base(self, category, products):
        self.state['raw_products'] += len(products)
        for p in products:
            try:
                product = Product.objects.get(tpid=p['tpid'], sid=self.site)
            except Product.DoesNotExist:
                product = Product(tpid=p['tpid'], sid=self.site)
            product.name = p['name']
            product.price = p['price']
            product.qty = 0
            product.cid = category
            if 'request_only' in p:
                product.request_only = p['request_only']
            else:
                product.request_only = False
            if 'second_price' in p:
                product.second_price = p['second_price']
            if 'request_line' in p:
                product.request_line = p['request_line']
            product.save()

    def update_category_url(self, category):
        return category.url

    # first page == 0
    def update_products(self, category, data):
        url = self.update_category_url(category)
        i = 1
        products = self.parse_products(data)
        self.update_products_base(category, products)
        url = self.next_products_page(category, url, i, data)
        while url and i <= self.max_pages and len(products) > 0:
            i += 1
            data = self.request(url)
            products = self.parse_products(data)
            self.update_products_base(category, products)
            url = self.next_products_page(category, url, i, data)

    def update_category(self, category):
        category.update = datetime.datetime.now()
        category.save()
        category.products.all().delete()
        url = self.update_category_url(category)
        doc = self.request(url)
        categories = self.parse_categories(doc)
        names, urls = self.update_base(categories)
        try:
            self.update_products(category, doc)
        except ParserSkipError as e:
            self.state['error_categories'].append([category.name, category.url])
        except ParserErrorLimit as e:
            raise e
        except Exception as e:
            now = self.now()
            self.add_error(u'Не удалось загрузить товары из категории "%s"' % category.name,
                           now, traceback.format_exc())
            self.state['error_categories'].append([category.name, category.url])
        return [names, urls]

    def update_site(self):
        url = self.root_url()
        doc = self.request(url)
        categories = self.parse_root(doc)
        names, urls = self.update_base(categories)
        Catalog.objects.filter(site=self.site).exclude(url__in=urls).delete()
        return [names, urls]

    def root_url(self):
        return self.site.url

    def parse_root(self, data):
        return self.parse_categories(data)

    def parse_categories(self, data):
        pass

    def parse_products(self, data):
        pass

    def parse_products_second(self, data):
        return self.parse_products

    def next_products_page(self, category, url, i, data):
        pass
