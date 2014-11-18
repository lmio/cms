#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2014 Vytis Banaitis <vytis.banaitis@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""A script to periodically extract statistics and send them to a graphite service

CMS config file must have a 'graphite_push' attribute, which is a (host, port) tuple.
Additionally, there can be a 'graphite_interval' attribute, which is time interval
between two data points, in seconds (by default, 1).

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function

# We enable monkey patching to make many libraries gevent-friendly
# (for instance, urllib3, used by requests)
import gevent.monkey
gevent.monkey.patch_all()

import logging
import socket
import sys
import time

from cms import config, ServiceCoord
from cms.db import SessionGen, get_active_contest_list
from cms.io import RemoteServiceClient


logger = logging.getLogger(__name__)


def worker_stats(workers):
    connected = 0
    busy = 0
    for worker in workers.itervalues():
        if worker['connected']:
            connected += 1
        if worker['job'] is not None:
            busy += 1
    return len(workers), connected, busy
    return dict(total=len(workers), connected=connected, busy=busy)


def get_stats(evaluation_service):
    workers = evaluation_service.workers_status()
    queue = evaluation_service.queue_status()
    submissions = {}
    with SessionGen() as session:
        for contest in get_active_contest_list(session):
            submissions[contest.name] = evaluation_service.submissions_status(contest_id=contest.id)

    stats = {}

    num_workers, connected, busy = worker_stats(workers.get())
    stats['workers.total'] = num_workers
    stats['workers.connected'] = connected
    stats['workers.busy'] = busy

    stats['queue.length'] = len(queue.get())

    for contest, submission_status in submissions.iteritems():
        status = submission_status.get()
        for key, value in status.iteritems():
            stats['contest.{}.submissions.{}'.format(contest, key)] = value

    return stats


def format_stats(stats):
    hostname = socket.gethostname().split('.', 1)[0]
    timestamp = int(time.time())

    lines = []
    for stat, value in stats.iteritems():
        lines.append('{}.cms.{} {} {}'.format(hostname, stat, value, timestamp))

    return '\n'.join(lines)


def send_stats(address, stats):
    data = format_stats(stats)
    s = socket.socket()
    try:
        s.connect(address)
        s.sendall(data)
    finally:
        s.close()


def main():
    if not hasattr(config, "graphite_push"):
        print("Please configure graphite.", file=sys.stderr)
        sys.exit(1)
    address = tuple(config.graphite_push)
    interval = getattr(config, "graphite_interval", 1)
    evaluation_service = RemoteServiceClient(ServiceCoord("EvaluationService", 0), auto_retry=0.5)
    evaluation_service.connect()

    try:
        while True:
            stats = get_stats(evaluation_service)
            send_stats(address, stats)
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        evaluation_service.disconnect()


if __name__ == "__main__":
    main()
