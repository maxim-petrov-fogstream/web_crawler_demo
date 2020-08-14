# -*- coding: utf-8 -*-

from task_manager_settings import *

import os
import time
import redis
import subprocess

r = redis.StrictRedis(host=host, port=port, db=0)
p = r.pubsub()
p.subscribe('tp-tasks-channel')

while True:
    try:
        for message in p.listen():
            try:
                if message['type'] == 'message':
                    id = message['data']
                    print 'id: %s' % id
                    subprocess.Popen(
                        ['python', os.path.join(project_path, 'manage.py'),
                         'tp_run_task', id]
                    )
            except:
                time.sleep(1)
    except Exception as e:
        time.sleep(1)
