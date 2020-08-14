import sys
import urllib, urllib2, cookielib
import re
import string
import lxml.html
from lxml import etree
import settings

class atape_http_client:
    def __init__(self, proxy=None, cookies=None, user_agent=None):
        self.cookie_handler   = urllib2.HTTPCookieProcessor(cookielib.CookieJar())
        self.redirect_handler = urllib2.HTTPRedirectHandler()
        self.http_handler     = urllib2.HTTPHandler()
        self.https_handler    = urllib2.HTTPSHandler()
        self.opener = urllib2.build_opener(self.http_handler,
                                           self.https_handler,
                                           self.cookie_handler,
                                           self.redirect_handler)
        if proxy:
            self.proxy_handler = urllib2.ProxyHandler(proxy)
            self.opener.add_handler(self.proxy_handler)

        # self.opener.addheaders = []

        if user_agent:
            self.opener.addheaders.append(('User-agent', user_agent))

        if cookies:
            self.opener.addheaders.append(('Cookie', cookies))

        urllib2.install_opener(self.opener)


    def request(self, url, params={}, timeout=180):
        error = None
        for x in range(0, settings.http_tries):
            try:
                if params:
                    params = urllib.urlencode(params)
                    html = urllib2.urlopen(url, params, timeout)
                else:
                    html = urllib2.urlopen(url)
                return html.read()
            except Exception as e:
                error = e
        raise error




def Parse_html(url, cookies=None, proxy=None):
    bot = atape_http_client(
        proxy={'http': settings.http_proxy},
        cookies=settings.cookies,
    )
    html = bot.request(url)
    return (html)
