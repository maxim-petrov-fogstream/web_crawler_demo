# -*- encoding: utf-8
import datetime
import logging
import traceback
import math

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from bs4 import BeautifulSoup

from .parser import Parser
from .models import Catalog, Product


logger = logging.getLogger('django')


options = Options()
options.headless = True


class ParserSkipError(Exception):
    pass


class ParserErrorLimit(Exception):
    pass


class RBT(Parser):

    browser = webdriver.Chrome(options=options)

    def __init__(self, site, task):
        super(RBT, self).__init__(site, task)
        self.browser.get(site.url)
        self.add_request(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), site.url, 'success')
        self.state['requests'] += 1
        self.update_categories(
            self.parse_categories(self.browser.page_source)
        )
        self.browser.quit()

    def add_request(self, url, now, result):
        reqs = self.state['last_requests']
        if len(reqs) >= self.max_last_items:
            reqs.pop(0)
        reqs.append({
            'time': now,
            'url': url,
            'result': result,
        })
        self.publish_state()

    def parse_categories(self, data):
        categories = []
        for tag in BeautifulSoup(data, "lxml").find_all("a", class_="catalogue-menu__tag-catalogue"):
            categories.append({
                'name': tag.text,
                'url': tag.attrs['href']
            })
        return categories

    def update_categories(self, categories):
        for category in categories:
            self.browser.get(self.site.url + category['url'])
            self.add_request(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.site.url + category['url'],
                             'success')
            category_obj, created = Catalog.objects.get_or_create(site=self.site, url=category['url'])
            category_obj.name = category['name']
            category_obj.save()
            self.state['requests'] += 1
            self.update_products(category_obj, self.browser.page_source)
            self.state['raw_categories'] += 1
            self.publish_state()

    def update_products(self, category, data):
        total_amount = int(BeautifulSoup(data, "lxml").find_all(
            "span", class_='item-catalogue-list__title-amount')[-1].text
        )
        last = 1
        if total_amount > 0:
            last = int(math.ceil(total_amount / 8.00)) + 1
        for i in range(1, last):
            is_error = False
            if i != 1:
                self.browser.get('{}{}~/page/{}/'.format(self.site.url, category.url, i))
                self.add_request(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                 '{}{}~/page/{}/'.format(self.site.url, category.url, i),
                                 'success')
            for item in BeautifulSoup(self.browser.page_source, "lxml").find_all("div", class_='item-catalogue'):
                try:
                    info = item.contents[1].contents[1].contents[0]
                    price = item.contents[2].contents[0].contents[0].contents[0].text
                    try:
                        product = Product.objects.get(tpid=info.attrs['href'], sid=self.site)
                    except Product.DoesNotExist:
                        product = Product(tpid=info.attrs['href'], sid=self.site)
                    product.name = info.attrs['title']
                    product.price = int(price.replace(' ', ''))
                    product.qty = 0
                    product.cid = category
                    product.save()
                    self.state['raw_products'] += 1
                except Exception as e:
                    is_error = True
                    continue
            if is_error:
                self.add_request(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                 '{}{}/~/page/{}/'.format(self.site.url, category.url, i),
                                 'error')
                self.state['last_errors'].append({
                    'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'short': 'Ошибка при загрузке товара "{}", в категории "{}"'.format(
                        info.attrs['title'].encode('utf-8'), category.name
                    ),
                    'info': traceback.format_exc()
                })
                self.state['total_errors'] += 1
                self.state['error_categories'].append([category.name, category.url])
            else:
                self.add_request(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.site.url + category.url,
                                 'success')
            self.publish_state()
