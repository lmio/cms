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
import re

import tornado.web

from sqlalchemy.orm import subqueryload

from cms import config
from cms.db import Contest, District, School, TeacherRegistration
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


class RegisterHandler(BaseHandler):

    email_re = re.compile(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")

    def render_params(self):
        params = super(RegisterHandler, self).render_params()
        district_list = (self.sql_session.query(District)
                         .options(subqueryload(District.schools))
                         .all())
        district_list.sort(key=lambda d: lt_sort_key(d.name))
        for d in district_list:
            d.schools.sort(key=lambda s: lt_sort_key(s.name))
        params["district_list"] = district_list
        return params

    def get(self):
        if not config.teacher_allow_registration:
            raise tornado.web.HTTPError(404)
        self.render("register.html", **self.r_params)

    def post(self):
        if not config.teacher_allow_registration:
            raise tornado.web.HTTPError(404)

        first_name = self.get_argument("first_name", "")
        last_name = self.get_argument("last_name", "")
        email = self.get_argument("email", "")
        district_id = self.get_argument("district", "")
        school_id = self.get_argument("school", "")

        try:
            # In py2 Tornado gives us the IP address as a native binary
            # string, whereas ipaddress wants text (unicode) strings.
            ip_address = ipaddress.ip_address(str(self.request.remote_ip))
        except ValueError:
            logger.warning("Invalid IP address provided by Tornado: %s",
                           self.request.remote_ip)
            return None

        errors = []
        if not first_name:
            errors.append("first_name")
        if not last_name:
            errors.append("last_name")
        if not email or not self.email_re.match(email):
            errors.append("email")

        try:
            district_id = int(district_id)
        except ValueError:
            errors.append("district")
            district = None
        else:
            district = District.get_from_id(district_id, self.sql_session)
            if district is None:
                errors.append("district")

        try:
            school_id = int(school_id)
        except ValueError:
            errors.append("school")
            school = None
        else:
            school = School.get_from_id(school_id, self.sql_session)
            if school is not None and district is not None and school.district != district:
                school = None
            if school is None:
                errors.append("school")

        if errors:
            self.render("register.html", errors=errors, **self.r_params)
            return

        registration = TeacherRegistration(first_name=first_name, last_name=last_name,
                                           email=email, district=district, school=school,
                                           timestamp=self.timestamp)
        self.sql_session.add(registration)
        self.sql_session.commit()

        logger.info("New teacher registered from IP address %s, for school %s, at %s.",
                    ip_address, school.name, self.timestamp)

        self.render("register.html", complete=True, **self.r_params)


class MainHandler(BaseHandler):
    """Home page handler.

    """
    @tornado.web.authenticated
    def get(self):
        self.r_params["contest_list"] = self.sql_session.query(Contest)\
                .filter(Contest.id.in_(config.teacher_active_contests)).all()
        self.render("contestlist.html", **self.r_params)
