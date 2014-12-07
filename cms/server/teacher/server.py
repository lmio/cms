#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2014-2018 Vytis Banaitis <vytis.banaitis@gmail.com>
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

"""TeacherWebServer serves the webpage that teachers are using to see
the results of their students.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future.builtins.disabled import *  # noqa
from future.builtins import *  # noqa

import logging

from cms import config
from cms.io import WebService
from cms.locale import get_translations
from cmscommon.binary import hex_to_bin

from .handlers import HANDLERS
from .jinja2_toolbox import TWS_ENVIRONMENT


logger = logging.getLogger(__name__)


class TeacherWebServer(WebService):
    """Service that runs the web server serving the teachers.

    """
    def __init__(self, shard):
        parameters = {
            "static_files": [("cms.server", "static"),
                             ("cms.server.contest", "static")],
            "cookie_secret": hex_to_bin(config.secret_key),
            "debug": config.tornado_debug,
            "is_proxy_used": config.is_proxy_used,
            "num_proxies_used": config.num_proxies_used,
            "xsrf_cookies": True,
        }

        super(TeacherWebServer, self).__init__(
            config.teacher_listen_port,
            HANDLERS,
            parameters,
            shard=shard,
            listen_address=config.teacher_listen_address)

        self.jinja2_environment = TWS_ENVIRONMENT

        self.translation = get_translations()[config.teacher_locale.replace("-", "_")]
