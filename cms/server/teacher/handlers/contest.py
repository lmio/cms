#!/usr/bin/env python2
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

"""Base class for all handlers in TWS, and some utility functions.

"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import logging
import pickle
import urlparse

import tornado.web

from sqlalchemy.orm import joinedload

from cms import config
from cms.db import Contest, Participation, User
from cms.server import CommonRequestHandler, filter_ascii
from cmscommon.datetime import make_timestamp

from .base import BaseHandler


logger = logging.getLogger(__name__)


def userattr(user):
    return getattr(user, config.teacher_login_kind)


class ContestHandler(BaseHandler):
    """Contest result list handler.

    """
    @tornado.web.authenticated
    def get(self, contest_id):
        if int(contest_id) not in config.teacher_active_contests:
            raise tornado.web.HTTPError(404)
        contest = Contest.get_from_id(contest_id, self.sql_session)
        if contest is None:
            raise tornado.web.HTTPError(404)

        self.r_params["contest"] = contest
        self.r_params["participations"] = self.sql_session.query(Participation)\
            .join(Participation.user)\
            .filter(Participation.contest == contest)\
            .filter(userattr(User) == self.current_user)\
            .options(joinedload('school')).all()
        self.render("contest.html", **self.r_params)


class ImpersonateHandler(BaseHandler):
    """Impersonate a contestant.

    """
    @tornado.web.authenticated
    def get(self, participation_id):
        p = Participation.get_from_id(participation_id, self.sql_session)
        if p is None:
            raise tornado.web.HTTPError(404)
        if (p.contest_id not in config.teacher_active_contests or
                userattr(p.user) != self.current_user):
            raise tornado.web.HTTPError(403)

        url = self.application.service.contest_url[p.contest_id]
        domain = urlparse.urlparse(url).hostname

        filtered_username = filter_ascii(p.user.username)
        logger.info("Teacher logged in as contestant: username=%s remote_ip=%s." %
                    (filtered_username, self.request.remote_ip))
        password = p.password if p.password is not None else p.user.password
        self.set_secure_cookie("login",
                               pickle.dumps((p.user.username,
                                             password,
                                             make_timestamp())),
                               domain=domain,
                               expires_days=None)
        # Bypass the overriden redirect because we are going outside
        # this web server.
        super(CommonRequestHandler, self).redirect(url)
