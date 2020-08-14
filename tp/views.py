# -*- coding: utf-8 -*-
################################################################################

import re
import datetime

import lxml.html
import xlwt
from StringIO import StringIO

from django.db.models import Q
from django.db.utils import IntegrityError
from django.shortcuts import render
from django.http import (
    HttpResponse,
    HttpResponseRedirect,
)
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import user_passes_test

from constance import config

from .models import *
from tp.get_redis import get_redis
from tp.tasks import (
    init_site_task, update_site_task, update_category_task,
    update_multiple_categories_task,
    task_full_info, task_short_info, task_cancel
)
from parseHtml import Parse_html
from decorators import *

import json
import logging
import csv

import traceback

logger = logging.getLogger('django')

################################################################################

def update_category_list(site):
    parser = site_parser_factory(site)
    return parser.init_site()

################################################################################

def available_proxies():
    used_proxies = {}
    for site in Site.objects.filter(active=True):
        if not site.opts: continue
        opts = site.opts
        opts = json.loads(site.opts)
        if 'http_proxy' in opts:
            proxy = opts['http_proxy']
            used_proxies[proxy] = True
            continue
        if 'https_proxy' in opts:
            proxy = opts['https_proxy']
            used_proxies[proxy] = True
            continue
    real_proxies = []
    available_proxies = []
    user = config.PROXY_USER
    password = config.PROXY_PASSWORD
    port = config.PROXY_PORT
    proxies = config.PROXY_LIST
    proxies = proxies.splitlines()
    proxies = map(lambda x: x.strip(), proxies)
    proxies = filter(
        lambda x: re.search(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', x) is not None, proxies
    )
    for proxy in proxies:
        proxy = user + ':' + password + '@' + proxy + ':' + port
        real_proxies.append(proxy)
        if proxy not in used_proxies:
            available_proxies.append(proxy)
    return available_proxies

@only_cnb
def settings(request):
    proxy_user = config.PROXY_USER
    proxy_password = config.PROXY_PASSWORD
    proxy_port = config.PROXY_PORT
    proxy_list = config.PROXY_LIST
    if request.method == 'POST':
        if 'proxy_user' in request.POST:
            proxy_user = request.POST['proxy_user']
            config.PROXY_USER = request.POST['proxy_user']
        if 'proxy_password' in request.POST:
            proxy_password = request.POST['proxy_password']
            config.PROXY_PASSWORD = request.POST['proxy_password']
        if 'proxy_port' in request.POST:
            proxy_port = request.POST['proxy_port']
            config.PROXY_PORT = request.POST['proxy_port']
        if 'proxy_list' in request.POST:
            proxy_list = request.POST['proxy_list']
            config.PROXY_LIST = request.POST['proxy_list']
    return render(
        request, 'tp/settings.html',
        {
            'proxy_user': proxy_user, 'proxy_password': proxy_password,
            'proxy_port': proxy_port, 'proxy_list': proxy_list,
        }
    )

@only_cnb
def init_site(request, id):
    site = Site.objects.get(id=id)
    if not site.active: raise Exception('Site is not active')
    task = init_site_task(site, 'site')
    return HttpResponseRedirect('/tp/task/' + str(task.id))

################################################################################

@only_cnb
def do_refresh_site(site):
    if site.active:
        update_site_task(site, 'site')

@only_cnb
def refresh_site(request, id):
    site = Site.objects.get(id=id)
    if not site.active: raise Exception('Site is not active')
    task = update_site_task(site, 'site')
    return HttpResponseRedirect('/tp/task/' + str(task.id))

@only_cnb
def settings_site(request, id):
    site = Site.objects.get(id=id)
    if not site.active: raise Exception('Site is not active')
    url = None
    if url is None: url = site.url
    proxy = None
    opts = site.opts
    if opts:
        opts = json.loads(opts)
    else:
        opts = {}
    if 'http_proxy' in opts: proxy = opts['http_proxy']
    elif 'https_proxy' in opts: proxy = opts['https_proxy']
    error = None
    if request.method == 'POST':
        if 'url' in request.POST:
            url = request.POST['url'].strip()
            site.url = url
        if 'proxy' in request.POST:
            proxy = request.POST['proxy'].strip()
            if len(proxy) == 0:
                opts.pop('http_proxy', None)
                opts.pop('https_proxy', None)
            else:
                opts['http_proxy'] = proxy
                opts.pop('https_proxy', None)
        site.opts = json.dumps(opts)
        try:
            site.save()
        except Exception as e:
            error = e.message
    if url is None: url = ''
    if proxy is None: proxy = ''
    return render(
        request, 'tp/site_settings.html',
        {
            'site': site, 'url': url, 'proxy': proxy, 'error': error,
            'available_proxies': available_proxies,
        }
    )

################################################################################

@only_cnb
def refresh(request, cat_id):
    category = Catalog.objects.get(id = cat_id)
    site = category.site
    if not site.active: raise Exception('Site is not active')
    task = update_category_task(site, category, 'site')
    return HttpResponseRedirect('/tp/task/' + str(task.id))

################################################################################

@only_cnb
def show_sites(request):
    sites = Site.objects.filter(active=True).order_by('name')
    return render(request, 'tp/sites.html', { 'sites': sites })

@only_cnb
def show_site(request, id):
    site = Site.objects.get(id=id)
    catalogs = Catalog.objects.filter(site=site).order_by('name')
    c = catalogs
    name = ''
    if 'name' in request.GET and request.GET['name'] != '':
        c = c.filter( name__icontains = request.GET['name'] )
        name = request.GET['name']
    return render(request, 'tp/categories.html', { 'site': site, 'c' : c,'name':name})

################################################################################

@only_cnb
def show_category(request, id):
    c = Catalog.objects.get(id=id)
    p = c.products.select_related()
    name = ''
    if 'name' in request.GET and request.GET['name'] != '':
        p = p.filter( name__icontains = request.GET['name'] )
        name = request.GET['name']
    return render(request, 'tp/category.html', { 'c' : c, 'p':p,'name':name})

################################################################################

@only_cnb
def show_product(request, id):
    p = Product.objects.get( id = id )
    return render(request, 'tp/product.html', { 'p':p })

################################################################################

@only_cnb
def category_csv(request, id):
    percent  = 60
    is_equal = 'off'
    opt      = 'off'
    sale     = 'off'
    inet     = 'off'

    if 'percent' in request.GET:
        percent  = int( request.GET['percent'] )
    if 'is_equal' in request.GET:
        is_equal = request.GET['is_equal']
    if 'opt' in request.GET:
        opt = request.GET['opt']
    if 'sale' in request.GET:
        sale = request.GET['sale']
    if 'inet' in request.GET:
        inet = request.GET['inet']

    include_reqon = (
        request.GET['include_reqon']
        if 'include_reqon' in request.GET
        else False
    )
    if include_reqon == 'on':
        include_reqon = True

    now = datetime.datetime.now()

    font0 = xlwt.Font()
    font0.colour_index = 0
    font0.bold = True

    style0 = xlwt.XFStyle()
    style0.font = font0

    wb = xlwt.Workbook()
    ws = wb.add_sheet(now.strftime('%Y-%m-%d %H_%M'))

    c = Catalog.objects.get( id = id )
    i = 0

    ws.write(i, 0, u'Название в ТП')
    ws.write(i, 1, u'Название в ЭНКА' )

    ws.write(i, 3, u'Цена в ТП')


    if opt == 'on':
        ws.write(i, 5, u'Цена в ЭНКА оптовая в руб.')
        ws.write(i, 9, u'Разница в цене между ЭНКА ОПТ и ТП в руб.' ,style0)
        ws.write(i, 10, u'Разница в цене между ЭНКА ОПТ и ТП в %' ,style0)
    else:
        ws.col(5).width = 0
        ws.col(9).width = 0
        ws.col(10).width = 0

    if inet == 'on':
        ws.write(i, 6, u'Цена в ЭНКА интернет в руб.')
        ws.write(i, 12, u'Разница в цене между ЭНКА ИНТЕРНЕТ и ТП в руб.' ,style0)
        ws.write(i, 13, u'Разница в цене между ЭНКА ИНТЕРНЕТ и ТП в %' ,style0)
    else:
        ws.col(6).width = 0
        ws.col(12).width = 0
        ws.col(13).width = 0

    if sale == 'on':
        ws.write(i, 7, u'Цена в ЭНКА розничная в руб.')
        ws.write(i, 15, u'Разница в цене между ЭНКА РОЗНИЦА и ТП в руб.' ,style0)
        ws.write(i, 16, u'Разница в цене между ЭНКА РОЗНИЦА и ТП в %' ,style0)
    else:
        ws.col(7).width = 0
        ws.col(15).width = 0
        ws.col(16).width = 0

    ws.col(2).width = 0
    ws.col(4).width = 0
    ws.col(8).width = 0
    ws.col(11).width = 0
    ws.col(14).width = 0
    ws.col(17).width = 0

    ws.write(i, 18, u'Кол-во в ЭНКА')
    ws.write(i, 19, u'Кол-во в ТП')

    ws.col(0).width = 10000
    ws.col(1).width = 10000

    ws.col(3).width = 3000

    ws.col(18).width = 3000
    ws.col(19).width = 3000
    i += 1

    for item in c.products.select_related():
        if (not include_reqon) and item.request_only:
            continue

        s = item.findCMP( percent=percent )
        if len(s):
            for p in s:
                ws.write(i, 0, item.name)
                ws.write(i, 1, p.name )

                ws.write(i, 3, item.price)

                if opt == 'on':
                    ws.write(i, 5, p.price_opt)
                    ws.write(i, 9,  xlwt.Formula(  ( "F%d-D%d" %( i+1,i+1 ) )  ),style0)
                    ws.write(i, 10, xlwt.Formula(  ( "ROUND(J%d/(D%d/100);1)" %( i+1,i+1 ) )  ),style0)

                if inet == 'on':
                    ws.write(i, 6, p.price_inet)
                    ws.write(i, 12, xlwt.Formula(  ( "G%d-D%d" %( i+1,i+1 ) )  ),style0)
                    ws.write(i, 13, xlwt.Formula(  ( "ROUND(M%d/(D%d/100);1)" %( i+1,i+1 ) )  ),style0)

                if sale == 'on':
                    ws.write(i, 7, p.price_sale)
                    ws.write(i, 15, xlwt.Formula(  ( "H%d-D%d" %( i+1,i+1 ) )  ),style0)
                    ws.write(i, 16, xlwt.Formula(  ( "ROUND(P%d/(D%d/100);1)" %( i+1,i+1 ) )  ),style0)

                ws.write(i, 18, item.qty)
                ws.write(i, 19, p.qty)

                i += 1

        elif is_equal != 'on':
            ws.write(i, 0, item.name)
            ws.write(i, 1, '---')

            ws.write(i, 3, item.price)

            ws.write(i, 19, item.qty)

            i+= 1
    buffer = StringIO()
    wb.save(buffer)
    response = HttpResponse(buffer.getvalue(), content_type='application/vnd.ms-excel')
    buffer.close()
    response['Content-Disposition'] = 'attachment; filename=%s.xls' % (
        (c.name.replace(' ', '_')
         + now.strftime('___%Y-%m-%d___%H-%M')).encode('utf-8')
    )
    return response

################################################################################

@csrf_exempt
@only_cnb
def full_price_list(request, id):
    if request.method == 'POST':
        if 'format' in request.POST and request.POST['format'] == 'csv':
            return get_price_list_csv_request(request, id)
        else:
            return get_price_list_request(request, id)
    else:
        return set_price_list(request, id)

@only_cnb
def category_price(request, id):
    format = 'xls'
    now = datetime.datetime.now()
    category = Catalog.objects.get(id=id)
    if 'format' in request.GET:
        format = request.GET['format']
    if format == 'csv':
        buffer = StringIO()
        get_price_list_csv([category.id], buffer)
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        buffer.close()
        response['Content-Disposition'] = 'attachment; filename=%s.csv' % (
            (u'Прайс-лист__' + now.strftime('%Y-%m-%d__%H-%M')).encode('utf-8')
        )
        return response
    else:
        wb = get_price_list([category.id])
        buffer = StringIO()
        wb.save(buffer)
        response = HttpResponse(buffer.getvalue(), content_type='application/vnd.ms-excel')
        buffer.close()
        response['Content-Disposition'] = 'attachment; filename=%s.xls' % (
            (u'Прайс-лист__' + now.strftime('%Y-%m-%d__%H-%M')).encode('utf-8')
        )
        return response

################################################################################

def set_price_list(request, id):
    site = Site.objects.get(id=id)
    format = 'xls'
    if 'format' in request.GET:
        format = request.GET['format']
    if 'name' in request.GET and request.GET['name']:
        name = request.GET['name']
        categories = Catalog.objects.filter(site=site, name__icontains=name)
    else:
        name = ''
        categories = Catalog.objects.filter(site=site)
    return render(request, 'tp/price_list.html', {
        'categories': categories.order_by('name'),
        'name'      : name,
        'format'    : format,
    })

################################################################################

def get_price_list_csv(cat_ids, csvfile):
    now = datetime.datetime.now()
    writer = csv.writer(csvfile, delimiter=';')
    for category in Catalog.objects.filter(id__in=cat_ids):
        writer.writerow([category.name.encode('cp1251', 'ignore')])
        writer.writerow([u'Название'.encode('cp1251', 'ignore'),
                         u'Цена (руб.)'.encode('cp1251', 'ignore'),
                         u'Цена со скидкой (руб.)'.encode('cp1251', 'ignore'),
                         u'Кол-во'.encode('cp1251', 'ignore'),
                         u'Под заказ'.encode('cp1251', 'ignore')])
        for item in category.products.all():
            if (not item.name):
                continue
            request_line = u''
            if len(item.request_line) > 0:
                request_line = item.request_line
            elif item.request_only:
                request_line = u'Да'
            writer.writerow([item.name.encode('cp1251', 'ignore'),
                             item.price,
                             item.second_price,
                             item.qty,
                             request_line.encode('cp1251', 'ignore')])
        writer.writerow([])

def get_price_list_csv_request(request, id):
    now = datetime.datetime.now()
    pattern = re.compile(r'add(\d+)$')
    cat_ids = []
    for key, value in request.POST.iteritems():
        match = pattern.match(key)
        if (match):
            try:
                cat_ids.append( int(match.group(1)) )
            except (ValueError, TypeError):
                pass
    buffer = StringIO()
    get_price_list_csv(cat_ids, buffer)
    response = HttpResponse(buffer.getvalue(), content_type='text/csv')
    buffer.close()
    response['Content-Disposition'] = 'attachment; filename=%s.csv' % (
        (u'Прайс-лист__' + now.strftime('%Y-%m-%d__%H-%M')).encode('utf-8')
    )
    return response

def get_price_list(xs):
    cat_ids = xs
    now = datetime.datetime.now()
    wb = xlwt.Workbook()
    (name_col, price_col, price_second_col, count_col, request_col) = range(5)
    sheet = 0
    row = 0

    bold_font = xlwt.Font()
    bold_font.colour_index = 0
    bold_font.bold = True

    bold_style = xlwt.XFStyle()
    bold_style.font = bold_font

    for category in Catalog.objects.filter(id__in=cat_ids):
        if (category.products.all().count() + 1 >= 65535):
            raise Exception("Category contains more than 65535 items, can't fit in xls")
        if (row == 0) or (category.products.all().count() + row + 1 >= 65535):
            sheet += 1
            ws = wb.add_sheet('%d' % sheet)
            row = 0

        ws.write(row, name_col,  category.name, bold_style)
        row += 1
        ws.write(row, name_col,  u'Название', bold_style)
        ws.write(row, price_col, u'Цена (руб.)', bold_style)
        ws.write(row, price_second_col, u'Цена со скидкой (руб.)', bold_style)
        ws.write(row, count_col, u'Кол-во', bold_style)
        ws.write(row, request_col, u'Под заказ', bold_style)
        ws.col(name_col).width  = 10000
        ws.col(price_col).width = 3000
        ws.col(price_second_col).width = 3000
        ws.col(count_col).width = 3000
        ws.col(request_col).width = 3000
        row += 1

        for item in category.products.all():
            if (not item.name):
                continue

            ws.write(row, name_col,  item.name)
            ws.write(row, price_col, item.price)
            ws.write(row, price_second_col, item.second_price)
            ws.write(row, count_col, item.qty)
            if len(item.request_line) > 0:
                ws.write(row, request_col, item.request_line)
            elif item.request_only:
                ws.write(row, request_col, u'Да')

            row += 1
    return wb

def get_price_list_request(request, id):
    now = datetime.datetime.now()
    pattern = re.compile(r'add(\d+)$')
    cat_ids = []
    for key, value in request.POST.iteritems():
        match = pattern.match(key)
        if (match):
            try:
                cat_ids.append( int(match.group(1)) )
            except (ValueError, TypeError):
                pass
    wb = get_price_list(cat_ids)

    buffer = StringIO()
    wb.save(buffer)
    response = HttpResponse(buffer.getvalue(), content_type='application/vnd.ms-excel')
    buffer.close()
    response['Content-Disposition'] = 'attachment; filename=%s.xls' % (
        (u'Прайс-лист__' + now.strftime('%Y-%m-%d__%H-%M')).encode('utf-8')
    )
    return response

@only_cnb
def show_task(request, id):
    task = Tasks.objects.get(id=id)
    r = get_redis()
    info = task_full_info(task, r)
    return render(request, 'tp/task.html', info)

@only_cnb
def show_tasks(request):
    try:
        page = int(request.GET.get('page', 1))
    except:
        page = 1
    if page < 1: page = 1
    per_page = 100
    tasks = (
        Tasks.objects
        .filter(status__in=['queued', 'started'])
        .order_by('-id')
        [(page - 1) * per_page : page * per_page]
    )
    r = get_redis()
    result = []
    for task in tasks:
        x = task_short_info(task, r)
        x['url'] = '/tp/task/' + str(task.id) + '/'
        x['id'] = task.id
        result.append(x)
    return render(request, 'tp/tasks.html', {
        'tasks': result, 'name': 'Список задач (активные)',
        'show_controls': True, 'path': request.path,
    })

@only_cnb
def show_old_tasks(request):
    try:
        page = int(request.GET.get('page', 1))
    except:
        page = 1
    if page < 1: page = 1
    per_page = 100
    tasks = (
        Tasks.objects
        .exclude(status__in=['queued', 'started'])
        .order_by('-id')
        [(page - 1) * per_page : page * per_page]
    )
    r = get_redis()
    result = []
    for task in tasks:
        x = task_short_info(task, r)
        x['url'] = '/tp/task/' + str(task.id) + '/'
        x['id'] = task.id
        result.append(x)
    return render(request, 'tp/tasks.html', {
        'tasks': result, 'name': 'Список задач (архив)',
        'show_controls': False, 'path': request.path,
    })

@only_cnb
def start_task(request):
    if request.method == 'POST':
        path = '/tp/tasks/'
        try:
            path = request.POST.get('path', path)
            id = request.POST['id']
            task = Tasks.objects.get(id=id)
            r = get_redis()
            r.publish('tp-tasks-channel', task.id)
            return HttpResponseRedirect(path)
        except:
            pass
        return HttpResponseRedirect('/tp/tasks/')
    else:
        return HttpResponseRedirect('/tp/tasks/')

@only_cnb
def stop_task(request):
    if request.method == 'POST':
        path = '/tp/tasks/'
        try:
            path = request.POST.get('path', path)
            id = request.POST['id']
            task = Tasks.objects.get(id=id)
            task_cancel(task)
            return HttpResponseRedirect(path)
        except:
            print traceback.format_exc()
            return HttpResponseRedirect(path)
    else:
        return HttpResponseRedirect('/tp/tasks/')

@only_cnb
def retry_error_categories(request):
    if request.method != 'POST':
        return HtppResponseRedirect('/tp/tasks/')
    id = request.POST['id']
    task = Tasks.objects.get(id=id)
    data = json.loads(task.data)
    if not('site_id' in data): raise Exception('No site_id in task')
    site_id = data['site_id']
    site = Site.objects.get(id=site_id)
    if not site.active: raise Exception('Site is not active')
    r = get_redis()
    if task.status == 'complete' or task.status == 'error':
        report = task.report
    else:
        report = r.get(task.redis_id())
    report = json.loads(report)
    categories = []
    if 'error_categories' in report:
        categories = report['error_categories']
    task = update_multiple_categories_task(site, categories, 'site')
    return HttpResponseRedirect('/tp/task/' + str(task.id))
