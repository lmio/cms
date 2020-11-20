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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future.builtins.disabled import *  # noqa
from future.builtins import *  # noqa

from .main import \
    MainHandler, \
    LoginHandler, \
    LogoutHandler, \
    RegisterHandler
from .contest import \
    ContestHandler, \
    TaskStatementHandler, \
    TaskAttachmentHandler, \
    ContestAttachmentHandler, \
    ContestantLeaveHandler, \
    ImpersonateHandler


HANDLERS = [
    (r"/", MainHandler),
    (r"/login", LoginHandler),
    (r"/logout", LogoutHandler),
    (r"/register", RegisterHandler),
    (r"/contest/([0-9]+)", ContestHandler),
    (r"/contest/([0-9]+)/([a-z]+)", ContestHandler),
    (r"/contest/([0-9]+)/task/(.+)/statement/(.+)", TaskStatementHandler),
    (r"/contest/([0-9]+)/task/(.+)/attachment/(.+)", TaskAttachmentHandler),
    (r"/contest/([0-9]+)/attachment/(.+)", ContestAttachmentHandler),
    (r"/impersonate/([0-9]+)", ImpersonateHandler),
    (r"/contestant_leave/([0-9]+)", ContestantLeaveHandler),
]


__all__ = ["HANDLERS"]
