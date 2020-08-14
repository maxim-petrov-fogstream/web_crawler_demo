# -*- coding: utf-8 -*-

import datetime
from django.db import connection
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import json
import logging
import os
import psutil
import pytz
import traceback


#From old tasks

import subprocess
import signal

from tp.get_redis import get_redis
from .models import Tasks, Site, Catalog
from .technopoint import Technopoint
from .lbzone import Lbzone
from .nk import NK
from .domotechnika import Domotechnika
from .yavits import Yavits
from .vlazer import VLazer
from .kb import KB
from .eldorado import Eldorado
from .mvideo import MVideo
from .rassvet import Rassvet
from .magazindv import MagazinDV

logger = logging.getLogger('django')

def add_task(data, source):
    task = Tasks.objects.create(
        data=json.dumps(data), source=source,
        created=datetime.datetime.now(), status='queued'
    )
    r = get_redis()
    r.publish('tp-tasks-channel', task.id)
    return task

def init_site_task(site, source):
    data = {
        "type": "init_site",
        "site_id": site.id,
        "site_name": site.name,
    }
    return add_task(data, source)

def update_site_task(site, source):
    data = {
        "type": "update_site",
        "site_id": site.id,
        "site_name": site.name,
    }
    return add_task(data, source)

def update_category_task(site, category, source):
    data = {
        "type": "update_category",
        "site_id": site.id,
        "site_name": site.name,
        "category_id": category.id,
        "category_name": category.name,
        "category_url": category.url,
    }
    return add_task(data, source)

def update_multiple_categories_task(site, categories, source):
    data = {
        "type": "update_multiple_categories",
        "site_id": site.id,
        "site_name": site.name,
        "categories": categories,
    }
    return add_task(data, source)

def site_parser_factory(site, task):
    d = {
        'technopoint': Technopoint,
        'lbzone': Lbzone,
        'nk': NK,
        'domotechnika': Domotechnika,
        'yavits': Yavits,
        'vlazer': VLazer,
        'kb': KB,
        'eldorado': Eldorado,
        'mvideo': MVideo,
        'rassvet': Rassvet,
        'magazindv': MagazinDV,
    }
    return d[site.parser](site, task)

def run_init_site(data, parser):
    parser.init_site()

def run_update_site(data, parser):
    parser.update_site()

def run_update_category(data, parser):
    category = Catalog.objects.get(id=data['category_id'])
    parser.update_category(category)

def run_update_multiple_categories(data, parser):
    parser.update_base(data['categories'])

def dispatch_task(data, task):
    task_types = {
        'init_site': run_init_site,
        'update_site': run_update_site,
        'update_category': run_update_category,
        'update_multiple_categories': run_update_multiple_categories,
    }
    if 'type' in data and data['type'] in task_types:
        site_id = data['site_id']
        site = Site.objects.get(id=site_id)
        parser = site_parser_factory(site, task)
        task_types[data['type']](data, parser)
        parser.publish_state()
    else:
        raise Exception('Wrong task type')

def get_task_report(r, id):
    try:
        data = r.get('tp-task-%s' % id)
        data = json.loads(data)
    except:
        data = {}
    return data

def do_run_task(id):
    pid = os.getpid()
    started = datetime.datetime.now()
    task = Tasks.objects.get(id=id)
    if task.status != "queued":
        raise Exception('Task was already started')
    r = get_redis()
    cursor = connection.cursor()
    task.status = 'started'
    task.process = pid
    task.started = started
    task.save()
    task = Tasks.objects.get(id=id)
    if str(task.process) != str(pid):
        raise Exception('Unable to lock task')
    try:
        data = json.loads(task.data)
        dispatch_task(data, task)
        task.finished = datetime.datetime.now()
        task.status = "complete"
        report = get_task_report(r, id)
        report['result'] = 'complete'
        task.report = json.dumps(report)
        task.save()
        data = json.loads(task.data)
        if Site.objects.get(id=data['site_id']).parser == 'rbt':
            kill_selenium_process()
        r.delete(task.redis_id())
    except Exception as e:
        task.finished = datetime.datetime.now()
        task.status = "error"
        report = get_task_report(r, id)
        report['result'] = 'error'
        report['error'] = u"Исключение"
        report['stacktrace'] = traceback.format_exc()
        task.report = json.dumps(report)
        task.save()
        r.delete(task.redis_id())

def run_task(id):
    try:
        do_run_task(id)
    except Exception as e:
        pid = os.getpid()
        first = 'run_task id: %s, pid: %s\n' % (id, pid)
        trace = traceback.format_exc()
        logger.info(first + trace)


def kill_selenium_process():
    print 'killing selenium tasks'
    p = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE)
    out, err = p.communicate()
    for line in out.splitlines():
        if 'firefox' in line or 'geckodriver' in line or 'Web Content' in line:
            try:
                pid = int(line.split(None, 1)[0])
                os.kill(pid, signal.SIGKILL)
            except Exception as e:
                continue

task_types = {
    'init_site': u'Инициализировать сайт',
    'update_site': u'Обновить сайт',
    'update_category': u'Обновить категорию',
    'update_multiple_categories': u'Обновить несколько категорий',
}

task_stati = {
    'queued': u'В очереди',
    'started': u'Выполняется',
    'complete': u'Завершена',
    'error': u'Ошибка',
}

def task_status(task):
    return task_stati.get(task.status, task.status)

task_sources = {
    'site': u'Сайт',
    'cron': u'По расписанию',
}

def task_source(task):
    return task_sources.get(task.source, task.source)

def pprint_bytes(x):
    if x / 1024.0 < 0.1: return x
    suffix = u'Байт'
    for s in ['KB', 'MB', 'GB']:
        if x / 1024.0 < 1: break
        x /= 1024.0
        suffix = s
    return u'%0.1lf %s' % (x, suffix)

def pprint_time(time):
    return time.strftime("%Y-%m-%d %H:%M:%S")

def task_full_info(task, r):
    result = {}
    data = json.loads(task.data)
    data_description = [
        ('site_id', u'Номер сайта'),
        ('site_name', u'Название сайта'),
        ('category_id', u'Номер категории'),
        ('category_name', u'Название категории'),
        ('category_url', u'Ссылка на категорию'),
    ]
    data_text = []
    t = data['type']
    t = task_types.get(t, t)
    data_text.append(u"Задача: " + t)
    for key, name in data_description:
        if key in data:
            data_text.append(u"%s: %s" % (name, data[key]))
    if 'categories' in data:
        data_text.append(u"Список категорий (%d):" % len(data['categories']))
        for [name, url] in data['categories']:
            data_text.append(u"  %s (%s)" % (url, name))
    data_text = u"\n".join(data_text)
    result['data'] = data_text
    if data['type'] == 'update_category':
        name = "%s (%s, %s)" % (t, data['site_name'], data['category_name'])
    else:
        name = "%s (%s)" % (t, data['site_name'])
    result['name'] = name
    result['id'] = task.id
    result['status'] = task_status(task)
    result['source'] = task_source(task)
    if task.status == 'started':
        result['process'] = task.process
        try:
            process = psutil.Process(int(task.process))
            result['process'] += u' (работает): ' + " ".join(process.cmdline())
        except:
            result['process'] += u' (завершен)'
    result['created'] = pprint_time(task.created)
    if task.started:
        result['started'] = pprint_time(task.started)
    if task.finished:
        result['finished'] = pprint_time(task.finished)
    if task.status == 'complete' or task.status == 'error':
        report = task.report
    else:
        report = r.get(task.redis_id())
    if report:
        try:
            report = json.loads(report)
            result['report'] = report
            if 'result' in report and report['result'] == 'stopped':
                result['status'] = u'Отменена'
            elif task.status == 'complete':
                if report.get('request_error', 0) > 0 or report.get('total_errors', 0) > 0:
                    result['status'] = u'Ошибка (частично)'
            report['bytes_transferred'] = pprint_bytes(report.get('bytes_transferred', 0))
        except:
            pass
    return result

def task_short_info(task, r):
    result = {}
    data = json.loads(task.data)
    t = data['type']
    t = task_types.get(t, t)
    if data['type'] == 'update_category':
        name = "%s (%s, %s)" % (t, data['site_name'], data['category_name'])
    else:
        name = "%s (%s)" % (t, data['site_name'])
    result['name'] = name
    result['status'] = task_status(task)
    result['created'] = pprint_time(task.created)
    if task.started:
        result['started'] = pprint_time(task.started)
    if task.finished:
        result['finished'] = pprint_time(task.finished)
    if task.status == 'complete' or task.status == 'error':
        report = task.report
    else:
        report = r.get(task.redis_id())
    if report:
        try:
            report = json.loads(report)
            result['report'] = report
            if 'result' in report and report['result'] == 'stopped':
                result['status'] = u'Отменена'
            elif task.status == 'complete':
                if report.get('request_error', 0) > 0 or report.get('total_errors', 0) > 0:
                    result['status'] = u'Ошибка (частично)'
            result['last_activity'] = report['last_activity']
        except:
            pass
    return result

def task_cancel_reason(task, result, reason):
    r = get_redis()
    try:
        p = psutil.Process(int(task.process))
        s = settings.TASK_SETTINGS
        cmd = s['cmdline'][:]
        cmd.append(str(task.id))
        if not(p.username() == s['user'] and p.cmdline() == cmd): Exception('Wrong process')
        p.kill()
    except:
        pass
    if task.status == 'queued' or task.status == 'started':
        report = get_task_report(r, task.id)
        if not report: report = {}
        task.status = 'error'
        task.finished = datetime.datetime.now()
        report['result'] = result
        report['error'] = reason
        task.report = json.dumps(report)
        task.save()
    r.delete(task.redis_id())

def task_cancel(task):
    task_cancel_reason(task, 'stopped', u'Задача отменена')

def cleanup_zombies():
    r = get_redis()
    tasks = Tasks.objects.filter(status='started')
    now = datetime.datetime.now()
    total = []
    for task in tasks:
        try:
            report = get_task_report(r, task.id)
            if not report or 'last_activity' not in report: continue
            last = report['last_activity']
            last = datetime.datetime.strptime(last, "%Y-%m-%d %H:%M:%S")
            delta = now - last
            delta = delta.total_seconds()
            if delta < (60 * 60): continue
            task_cancel_reason(task, 'zombie', 'Задача зависла')
            total.append(task)
            logger.info(u'Убита задача-зомби %s' % task.id)
        except:
            pass

def cleanup_redis_keys():
    r = get_redis()
    keys = r.keys('tp-task-*')
    d = {'queued': True, 'started': True}
    for key in keys:
        try:
            id = int(key[8:])
            task = Tasks.objects.get(id=id)
            if task.status not in d: r.delete(key)
        except ObjectDoesNotExist:
            r.delete(key)
        except:
            pass
