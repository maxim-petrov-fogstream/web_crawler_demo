# -*- encoding: utf-8


import cookielib
from django.db.models import Q
import gzip
import json
import lxml.html
from lxml import etree
import re
from StringIO import StringIO
import urllib2

from tp.models import Site

user_agent = (
    'Mozilla/5.0 (X11; Linux i686) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/46.0.2490.71 Safari/537.36'
)


def request(url, proxy):
    proxy = urllib2.ProxyHandler({'http': proxy})
    cookiejar = cookielib.CookieJar()
    cookiejar = urllib2.HTTPCookieProcessor(cookiejar)
    opener = urllib2.build_opener(proxy, cookiejar)
    request = urllib2.Request(url, headers={
        'Accept-Encoding': 'gzip',
        'User-Agent': user_agent,
    })
    response = opener.open(request, None, 30)
    data = response.read()
    if response.info().getheader('Content-encoding') == 'gzip':
        data = gzip.GzipFile(fileobj=StringIO(data)).read()
    return data

def parse_free_proxy(data, doc):
    xs = doc.xpath(
        './/*[contains(concat(" ", normalize-space(@class), " "), " table ")]'
        '//*[contains(concat(" ", normalize-space(@class), " "), " hover ")]'
    )
    result = []
    a = re.search('var a = "(\d+)"', data)
    a = int(a.group(1))
    f = re.search('var f(\d+) = (\d+)', data)
    f = int(f.group(2))
    for x in xs:
        tds = x.xpath('.//*[contains(concat(" ", normalize-space(@class), " "), " td ")]')
        host = tds[0].xpath('./text()')[0].strip()
        port = tds[1].xpath('./script/text()')[0].strip()
        port = re.search('document\.write\((\d+)', port)
        port = int(port.group(1))
        port = port - a - f
        port = str(port)
        if len(port) == 0: continue
        result.append(host + ":" + port)
    print 'parse_free_proxy'
    print result
    return result

def parse_hideme(data, doc):
    xs = doc.xpath(
        './/table[contains(concat(" ", normalize-space(@class), " "), " proxy__t ")]'
        '//tbody/tr'
    )
    result = []
    for x in xs:
        tds = x.xpath('./td')
        host = tds[0].xpath('./text()')[0].strip()
        port = tds[1].xpath('./text()')[0].strip()
        result.append(host + ":" + port)
    print 'parse_hideme'
    print result
    return result

def check_proxy(proxy):
    urls = [
        ["http://habarovsk.domotekhnika.ru/", "C0v30SbCdxMJ0-lRzMf365gx2iermM8mxqAf0XBOql4"],
        ["http://www.eldorado.ru/", "EZ9W1uE3i7OLpA2rgDl5ljXzb6JleN-LIPRgdBWDmvk"],
    ]
    try:
        for i in range(0, 2):
            for [url, s] in urls:
                print [proxy, url]
                data = request(url, proxy)
                if data.find(s) == -1:
                    raise Exception('error')
        return True
    except Exception as e:
        print e
        return False

def check_proxies(xs):
    result = []
    i = 0
    for proxy in xs:
        i = i + 1
        if check_proxy(proxy):
            result.append(proxy)
            print proxy
    return result

def get_proxy_page(url):
    request = urllib2.Request(url, headers={
        'Accept-Encoding': 'gzip',
        'User-Agent': user_agent,
    })
    response = urllib2.urlopen(request)
    data = response.read()
    if response.info().getheader('Content-encoding') == 'gzip':
        data = gzip.GzipFile(fileobj=StringIO(data)).read()
    return data

def get_proxy_list():
    xs = [
        [parse_free_proxy, "http://www.freeproxy-list.ru/proxy-list-country/RU"],
        [parse_free_proxy, "http://www.freeproxy-list.ru/proxy-list-country/UA"],
        [parse_hideme, "http://hideme.ru/proxy-list/?country=RUUA&maxtime=2000&type=h#list"]
    ]
    parser = lxml.html.HTMLParser(recover=True)
    result = []
    for x in xs:
        [f, url] = x
        print url
        data = get_proxy_page(url)
        doc = etree.fromstring(data, parser)
        result += f(data, doc)
    result = list(set(result))
    return result

def get_valid_proxies():
    xs = get_proxy_list()
    return check_proxies(xs)

def check_existing_proxies():
    sites = Site.objects.filter(
        Q(parser='domotechnika', active=True) | Q(parser='eldorado', active=True)
    )
    ok = []
    for_update = []
    proxies = []
    for site in sites:
        opts = json.loads(site.opts)
        if 'proxy' in opts:
            proxy = opts['proxy']
            proxies.append(proxy)
            if not check_proxy(proxy):
                for_update.append(site)
        else:
            for_update.append(site)
    return [for_update, proxies]

def update_proxies():
    [sites, bl] = check_existing_proxies()
    proxies = get_valid_proxies()
    proxies = list(set(proxies) - set(bl))
    for [site, proxy] in zip(sites, proxies):
        opts = json.loads(site.opts)
        opts['proxy'] = proxy
        site.opts = json.dumps(opts)
        site.save()
