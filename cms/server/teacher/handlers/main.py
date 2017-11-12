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
import re

import tornado.web

from sqlalchemy.orm import subqueryload

from cms import config
from cms.db import Contest, District, School, TeacherRegistration
from cms.server import filter_ascii
from cmscommon.datetime import make_timestamp, make_datetime

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


class RegisterHandler(BaseHandler):

    email_re = re.compile(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")

    def render_params(self):
        params = super(RegisterHandler, self).render_params()
        params["district_list"] = (self.sql_session.query(District)
                                   .options(subqueryload(District.schools))
                                   .all())
        return params

    def get(self):
        if not config.teacher_allow_registration:
            raise tornado.web.HTTPError(404)
        self.render("register.html", errors=[], complete=False, **self.r_params)

    def post(self):
        if not config.teacher_allow_registration:
            raise tornado.web.HTTPError(404)

        first_name = self.get_argument("first_name", "")
        last_name = self.get_argument("last_name", "")
        email = self.get_argument("email", "")
        district_id = self.get_argument("district", "")
        school_id = self.get_argument("school", "")

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
            self.render("register.html", errors=errors, complete=False, **self.r_params)
            return

        registration = TeacherRegistration(first_name=first_name, last_name=last_name,
                                           email=email, district=district, school=school,
                                           timestamp=make_datetime())
        self.sql_session.add(registration)
        self.sql_session.commit()

        filtered_name = filter_ascii("%s %s" % (first_name, last_name))
        filtered_email = filter_ascii(email)
        filtered_school = filter_ascii(school.name)
        logger.info("New teacher registered: name=%s email=%s school=%s remote_ip=%s." %
                    (filtered_name, filtered_email, filtered_school, self.request.remote_ip))

        self.render("register.html", errors=[], complete=True, **self.r_params)


class MainHandler(BaseHandler):
    """Home page handler.

    """
    @tornado.web.authenticated
    def get(self):
        self.r_params["contest_list"] = self.sql_session.query(Contest)\
                .filter(Contest.id.in_(config.teacher_active_contests)).all()
        self.render("contestlist.html", **self.r_params)
