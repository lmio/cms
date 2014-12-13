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

"""Base class for all handlers in TWS, and some utility functions.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future.builtins.disabled import *  # noqa
from future.builtins import *  # noqa

import ipaddress
import logging

import tornado.web

from sqlalchemy.orm import subqueryload

from cms import config
from cms.db import Contest, District
from cms.util import lt_sort_key

from ..authentication import validate_login
from .base import BaseHandler


logger = logging.getLogger(__name__)


class LoginHandler(BaseHandler):
    """Login handler.

    """
    def get(self):
        districts = self.sql_session.query(District)
        if config.teacher_login_kind == "school":
            districts = districts.options(subqueryload(District.schools))
        districts = districts.all()
        districts.sort(key=lambda d: lt_sort_key(d.name))
        if config.teacher_login_kind == "school":
            for d in districts:
                d.schools.sort(key=lambda s: lt_sort_key(s.name))
        self.r_params["district_list"] = districts
        self.r_params["login_kind"] = config.teacher_login_kind
        self.render("login.html", **self.r_params)

    def post(self):
        error_args = {"error": "true"}
        next_page = self.get_argument("next", None)
        if next_page is not None:
            error_args["next"] = next_page
            if next_page != "/":
                next_page = self.url(*next_page.strip("/").split("/"))
            else:
                next_page = self.url()
        else:
            next_page = self.url()
        error_page = self.url("login", **error_args)

        login_id = self.get_argument(config.teacher_login_kind, "")
        password = self.get_argument("password", "")

        try:
            # In py2 Tornado gives us the IP address as a native binary
            # string, whereas ipaddress wants text (unicode) strings.
            ip_address = ipaddress.ip_address(str(self.request.remote_ip))
        except ValueError:
            logger.warning("Invalid IP address provided by Tornado: %s",
                           self.request.remote_ip)
            return None

        obj, cookie = validate_login(
            self.sql_session, self.timestamp, login_id, password, ip_address)

        if cookie is None:
            self.clear_cookie("tws_login")
        else:
            self.set_secure_cookie("tws_login", cookie, expires_days=None)

        if obj is None:
            self.redirect(error_page)
        else:
            self.redirect(next_page)


class LogoutHandler(BaseHandler):
    """Logout handler.

    """
    def post(self):
        self.clear_cookie("tws_login")
        self.redirect(self.url("login"))


class MainHandler(BaseHandler):
    """Home page handler.

    """
    @tornado.web.authenticated
    def get(self):
        self.r_params["contest_list"] = self.sql_session.query(Contest)\
                .filter(Contest.id.in_(config.teacher_active_contests)).all()
        self.render("contestlist.html", **self.r_params)
