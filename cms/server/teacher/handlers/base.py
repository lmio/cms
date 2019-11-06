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

import logging
import traceback

import tornado.web

from cms.locale import DEFAULT_TRANSLATION
from cms.server import CommonRequestHandler

from ..authentication import authenticate_request


logger = logging.getLogger(__name__)


class BaseHandler(CommonRequestHandler):
    """Base RequestHandler for this application.

    All the RequestHandler classes in this application should be a
    child of this class.

    """

    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)
        self.translation = self.service.translation
        self._ = self.translation.gettext
        self.n_ = self.translation.ngettext

    def render(self, template_name, **params):
        t = self.service.jinja2_environment.get_template(template_name)
        for chunk in t.generate(**params):
            self.write(chunk)

    def prepare(self):
        """This method is executed at the beginning of each request.

        """
        super(BaseHandler, self).prepare()

        self.r_params = self.render_params()

    def get_current_user(self):
        """Gets the current district or school logged in from the
        cookies.

        If a valid cookie is retrieved, return a District or School
        object with the id specified in the cookie. Otherwise, return
        None.

        """
        cookie = self.get_secure_cookie("tws_login")
        if cookie is None:
            return None

        obj, cookie = authenticate_request(self.sql_session, self.timestamp, cookie)

        if cookie is None:
            self.clear_cookie("tws_login")
        elif self.refresh_cookie:
            self.set_secure_cookie("tws_login", cookie, expires_days=None)

        return obj

    def render_params(self):
        """Return the default render params used by almost all handlers.

        return (dict): default render params

        """
        ret = {}
        ret["now"] = self.timestamp
        ret["url"] = self.url

        ret["translation"] = self.translation
        ret["gettext"] = self._
        ret["ngettext"] = self.n_

        ret["xsrf_form_html"] = self.xsrf_form_html()

        if self.current_user is not None:
            ret['current_user'] = self.current_user

        # FIXME The handler provides too broad an access: its usage
        # should be extracted into with narrower-scoped parameters.
        ret["handler"] = self

        return ret

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
        if self.r_params is not None:
            self.render("error.html", status_code=status_code, **self.r_params)
        else:
            self.write("A critical error has occurred :-(")
            self.finish()

    def get_login_url(self):
        """Return the URL unauthenticated users are redirected to.

        """
        return self.url("login")
