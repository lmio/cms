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

"""TeacherWebServer serves the webpage that teachers are using to see
the results of their students.

"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import base64
import logging
import pickle
import pkg_resources
import traceback
from datetime import timedelta

import tornado.web

from cms import config
from cms.io import WebService
from cms.db import Session, District
from cms.server import CommonRequestHandler, get_url_root, filter_ascii
from cmscommon.datetime import make_datetime, make_timestamp


logger = logging.getLogger(__name__)


class BaseHandler(CommonRequestHandler):
    """Base RequestHandler for this application.

    All the RequestHandler classes in this application should be a
    child of this class.

    """

    def prepare(self):
        """This method is executed at the beginning of each request.

        """
        self.set_header("Cache-Control", "no-cache, must-revalidate")

        self.sql_session = Session()

        self._ = self.locale.translate

        self.r_params = self.render_params()

    def get_current_user(self):
        """Gets the current district logged in from the cookies

        If a valid cookie is retrieved, return a District object with
        the id specified in the cookie. Otherwise, return None.

        """
        if self.get_secure_cookie("tws_login") is None:
            return None

        # Parse cookie.
        try:
            cookie = pickle.loads(self.get_secure_cookie("tws_login"))
            district_id = cookie[0]
            password = cookie[1]
            last_update = make_datetime(cookie[2])
        except:
            self.clear_cookie("tws_login")
            return None

        # Check if the cookie is expired.
        if make_datetime() - last_update > \
                timedelta(seconds=config.cookie_duration):
            self.clear_cookie("login")
            return None

        # Load the district from DB.
        district = District.get_from_id(district_id, self.sql_session)

        # Check if district exists and password is correct.
        if district is None or district.password != password:
            self.clear_cookie("tws_login")
            return None

        # Refresh cookie
        self.set_secure_cookie("tws_login",
                               pickle.dumps((district.id,
                                             district.password,
                                             make_timestamp())),
                               expires_days=None)

        return district

    def render_params(self):
        """Return the default render params used by almost all handlers.

        return (dict): default render params

        """
        params = {}
        params["timestamp"] = make_datetime()
        params["url_root"] = get_url_root(self.request.path)
        return params

    def finish(self, *args, **kwds):
        """Finish this response, ending the HTTP request.

        We override this method in order to properly close the database.

        """
        self.sql_session.close()
        try:
            tornado.web.RequestHandler.finish(self, *args, **kwds)
        except IOError:
            # When the client closes the connection before we reply,
            # Tornado raises an IOError exception, that would pollute
            # our log with unnecessarily critical messages
            logger.debug("Connection closed before our reply.")

    def write_error(self, status_code, **kwargs):
        if "exc_info" in kwargs and \
                kwargs["exc_info"][0] != tornado.web.HTTPError:
            exc_info = kwargs["exc_info"]
            logger.error(
                "Uncaught exception (%r) while processing a request: %s" %
                (exc_info[1], ''.join(traceback.format_exception(*exc_info))))

        # Most of the handlers raise a 404 HTTP error before r_params
        # is defined. If r_params is not defined we try to define it
        # here, and if it fails we simply return a basic textual error notice.
        if hasattr(self, 'r_params'):
            self.render("error.html", status_code=status_code, **self.r_params)
        else:
            try:
                self.r_params = self.render_params()
                self.render("error.html", status_code=status_code,
                            **self.r_params)
            except:
                self.write("A critical error has occurred :-(")
                self.finish()


class TeacherWebServer(WebService):
    """Service that runs the web server serving the teachers.

    """
    def __init__(self, shard):
        parameters = {
            "login_url": "/login",
            "template_path": pkg_resources.resource_filename(
                "cms.server", "templates/teacher"),
            "static_path": pkg_resources.resource_filename(
                "cms.server", "static"),
            "cookie_secret": base64.b64encode(config.secret_key),
            "debug": config.tornado_debug,
            "is_proxy_used": config.is_proxy_used,
        }
        super(TeacherWebServer, self).__init__(
            config.teacher_listen_port,
            _tws_handlers,
            parameters,
            shard=shard,
            listen_address=config.teacher_listen_address)


class LoginHandler(BaseHandler):
    """Login handler.

    """
    def get(self):
        self.r_params["district_list"] = self.sql_session.query(District).all()
        self.render("login.html", **self.r_params)

    def post(self):
        district_id = self.get_argument("district", "")
        password = self.get_argument("password", "")
        next_page = self.get_argument("next", "/")

        filtered_district = filter_ascii(district_id)
        filtered_password = filter_ascii(password)
        try:
            district_id = int(district_id)
        except ValueError:
            logger.info("Login error: id=%s pass=%s remote_ip=%s" %
                        (filtered_district, filtered_password, self.request.remote_ip))
            self.redirect("/login?error=true")
            return

        district = District.get_from_id(district_id, self.sql_session)

        if district is None or district.password != password:
            logger.info("Login error: id=%s pass=%s remote_ip=%s" %
                        (filtered_district, filtered_password, self.request.remote_ip))
            self.redirect("/login?error=true")
            return

        logger.info("Teacher logged in: id=%s remote_ip=%s." %
                    (filtered_district, self.request.remote_ip))
        self.set_secure_cookie("tws_login",
                               pickle.dumps((district.id,
                                             district.password,
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
        self.render("overview.html", **self.r_params)


_tws_handlers = [
    (r"/", MainHandler),
    (r"/login", LoginHandler),
    (r"/logout", LogoutHandler),
]
