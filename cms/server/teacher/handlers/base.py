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
import traceback

from datetime import timedelta

import tornado.web

from cms import config
from cms.db import District, School
from cms.server import CommonRequestHandler, get_url_root
from cmscommon.datetime import make_datetime, make_timestamp


logger = logging.getLogger(__name__)


def get_user_from_db(object_id, session):
    if config.teacher_login_kind == "district":
        return District.get_from_id(object_id, session)
    elif config.teacher_login_kind == "school":
        return School.get_from_id(object_id, session)
    else:
        return None


class BaseHandler(CommonRequestHandler):
    """Base RequestHandler for this application.

    All the RequestHandler classes in this application should be a
    child of this class.

    """

    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)
        self._ = None

    def prepare(self):
        """This method is executed at the beginning of each request.

        """
        super(BaseHandler, self).prepare()

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
            kind = cookie[0]
            object_id = cookie[1]
            password = cookie[2]
            last_update = make_datetime(cookie[3])
            assert kind == config.teacher_login_kind
        except:
            self.clear_cookie("tws_login")
            return None

        # Check if the cookie is expired.
        if make_datetime() - last_update > \
                timedelta(seconds=config.cookie_duration):
            self.clear_cookie("tws_login")
            return None

        # Load the district or school from DB.
        obj = get_user_from_db(object_id, self.sql_session)

        # Check if district exists and password is correct.
        if obj is None or obj.password != password:
            self.clear_cookie("tws_login")
            return None

        # Refresh cookie
        self.set_secure_cookie("tws_login",
                               pickle.dumps((config.teacher_login_kind,
                                             obj.id,
                                             obj.password,
                                             make_timestamp())),
                               expires_days=None)

        return obj

    def render_params(self):
        """Return the default render params used by almost all handlers.

        return (dict): default render params

        """
        params = {}
        params["timestamp"] = self.timestamp
        params["url_root"] = get_url_root(self.request.path)
        return params

    def finish(self, *args, **kwds):
        """Finish this response, ending the HTTP request.

        We override this method in order to properly close the database.

        """
        if hasattr(self, "sql_session"):
            try:
                self.sql_session.close()
            except Exception as error:
                logger.warning("Couldn't close SQL connection: %r", error)
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

        # We assume that if r_params is defined then we have at least
        # the data we need to display a basic template with the error
        # information. If r_params is not defined (i.e. something went
        # *really* bad) we simply return a basic textual error notice.
        if getattr(self, 'r_params', None) is not None:
            self.render("error.html", status_code=status_code, **self.r_params)
        else:
            self.write("A critical error has occurred :-(")
            self.finish()
