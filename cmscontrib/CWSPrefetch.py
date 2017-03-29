#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2017 Vytis Banaitis <vytis.banaitis@gmail.com>
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

"""A script to prefetch files relevant to CWS to ease contest start."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function
from future.builtins.disabled import *  # noqa
from future.builtins import *  # noqa

# We enable monkey patching to make many libraries gevent-friendly
# (for instance, urllib3, used by requests)
import gevent.monkey
gevent.monkey.patch_all()  # noqa

import logging
import os

from cms import config
from cms.db import SessionGen, get_active_contest_list
from cms.db.filecacher import FileCacher

logger = logging.getLogger(__name__)


def collect_digests():
    digests = set()
    with SessionGen() as s:
        for contest in get_active_contest_list(s):
            for task in contest.tasks:
                for statement in task.statements.itervalues():
                    digests.add(statement.digest)
                for attachment in task.attachments.itervalues():
                    digests.add(attachment.digest)
            for attachment in contest.attachments.itervalues():
                digests.add(attachment.digest)
    return digests


def get_cws_shards():
    # Search for CWS cache directories.
    # This approach only finds CWSs that have been started at least once.
    prefix = 'fs-cache-ContestWebServer-'
    for fn in os.listdir(config.cache_dir):
        if not fn.startswith(prefix):
            continue
        shard = fn[len(prefix):]
        try:
            shard = int(shard)
        except ValueError:
            continue
        if not os.path.isdir(os.path.join(config.cache_dir, fn)):
            continue
        yield shard


class FakeCWS(object):
    """A mock object that impersonates a CWS to a FileCacher."""

    name = 'ContestWebServer'

    def __init__(self, shard):
        self.shard = shard


def main():
    digests = collect_digests()

    logger.info('Prefetching %d files.', len(digests))

    master_cacher = FileCacher()
    for digest in digests:
        master_cacher.load(digest)

    for shard in get_cws_shards():
        logger.info('Updating CWS %d cache.', shard)

        cws_cacher = FileCacher(FakeCWS(shard), master_cacher.file_dir)
        for digest in digests:
            cws_cacher.load(digest, if_needed=True)

    logger.info('Cleaning up.')

    master_cacher.destroy_cache()


if __name__ == '__main__':
    main()
