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

import tornado.web

from sqlalchemy.orm import subqueryload

from cms.db import District
from cms.server import filter_ascii
from cmscommon.datetime import make_timestamp

from .base import BaseHandler, get_user_from_db


logger = logging.getLogger(__name__)


class LoginHandler(BaseHandler):
    """Login handler.

    """
    def get(self):
        districts = self.sql_session.query(District)
        if config.teacher_login_kind == "school":
            districts = districts.options(subqueryload(District.schools))
        self.r_params["district_list"] = districts.all()
        self.r_params["login_kind"] = config.teacher_login_kind
        self.render("login.html", **self.r_params)

    def post(self):
        login_id = self.get_argument(config.teacher_login_kind, "")
        password = self.get_argument("password", "")
        next_page = self.get_argument("next", "/")

        filtered_login = filter_ascii(login_id)
        filtered_password = filter_ascii(password)
        try:
            login_id = int(login_id)
        except ValueError:
            logger.info("Login error: id=%s pass=%s remote_ip=%s" %
                        (filtered_login, filtered_password, self.request.remote_ip))
            self.redirect("/login?error=true")
            return

        obj = get_user_from_db(login_id, self.sql_session)

        if obj is None or obj.password != password:
            logger.info("Login error: id=%s pass=%s remote_ip=%s" %
                        (filtered_login, filtered_password, self.request.remote_ip))
            self.redirect("/login?error=true")
            return

        logger.info("Teacher logged in: id=%s remote_ip=%s." %
                    (filtered_login, self.request.remote_ip))
        self.set_secure_cookie("tws_login",
                               pickle.dumps((config.teacher_login_kind,
                                             obj.id,
                                             obj.password,
                                             make_timestamp())),
                               expires_days=None)
        self.redirect(next_page)


class LogoutHandler(BaseHandler):
    """Logout handler.

    """
    def get(self):
        self.clear_cookie("tws_login")
        self.redirect("/login")


class MainHandler(BaseHandler):
    """Home page handler.

    """
    @tornado.web.authenticated
    def get(self):
        self.render("contestlist.html", **self.r_params)
