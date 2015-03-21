#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2010-2014 Giovanni Mascellani <mascellani@poisson.phc.unipi.it>
# Copyright © 2010-2018 Stefano Maggiolo <s.maggiolo@gmail.com>
# Copyright © 2010-2012 Matteo Boscariol <boscarim@hotmail.com>
# Copyright © 2012-2014 Luca Wehrstedt <luca.wehrstedt@gmail.com>
# Copyright © 2013 Bernard Blackham <bernard@largestprime.net>
# Copyright © 2014 Artem Iglikov <artem.iglikov@gmail.com>
# Copyright © 2014 Fabian Gundlach <320pointsguy@gmail.com>
# Copyright © 2015-2016 William Di Luigi <williamdiluigi@gmail.com>
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

"""Non-categorized handlers for CWS.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future.builtins.disabled import *  # noqa
from future.builtins import *  # noqa

import ipaddress
import json
import logging
import random
import re

import tornado.web

from sqlalchemy.orm import subqueryload

from cms import config
from cms.db import PrintJob, User, Participation, District, School
from cms.grading.steps import COMPILATION_MESSAGES, EVALUATION_MESSAGES
from cms.server import multi_contest
from cms.server.contest.authentication import validate_login
from cms.server.contest.communication import get_communications
from cms.server.contest.printing import accept_print_job, PrintingDisabled, \
    UnacceptablePrintJob
from cms.util import lt_sort_key
from cmscommon.crypto import build_password, parse_authentication
from cmscommon.datetime import make_datetime, make_timestamp
from cmscommon.mimetypes import get_type_for_file_name

from ..phase_management import actual_phase_required

from .contest import ContestHandler, FileHandler


logger = logging.getLogger(__name__)


# Dummy function to mark translatable strings.
def N_(msgid):
    return msgid


class MainHandler(ContestHandler):
    """Home page handler.

    """
    @multi_contest
    def get(self):
        self.render("overview.html", **self.r_params)


class LoginHandler(ContestHandler):
    """Login handler.

    """
    @multi_contest
    def post(self):
        error_args = {"login_error": "true"}
        next_page = self.get_argument("next", None)
        if next_page is not None:
            error_args["next"] = next_page
            if next_page != "/":
                next_page = self.url(*next_page.strip("/").split("/"))
            else:
                next_page = self.url()
        else:
            next_page = self.contest_url()
        error_page = self.contest_url(**error_args)

        username = self.get_argument("username", "")
        password = self.get_argument("password", "")

        try:
            # In py2 Tornado gives us the IP address as a native binary
            # string, whereas ipaddress wants text (unicode) strings.
            ip_address = ipaddress.ip_address(str(self.request.remote_ip))
        except ValueError:
            logger.warning("Invalid IP address provided by Tornado: %s",
                           self.request.remote_ip)
            return None

        participation, cookie = validate_login(
            self.sql_session, self.contest, self.timestamp, username, password,
            ip_address)

        cookie_name = self.contest.name + "_login"
        if cookie is None:
            self.clear_cookie(cookie_name)
        else:
            self.set_secure_cookie(cookie_name, cookie, expires_days=None)

        if participation is None:
            self.redirect(error_page)
        else:
            self.redirect(next_page)


class RegisterHandler(ContestHandler):

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

    @multi_contest
    def get(self):
        if not self.contest.allow_registration:
            raise tornado.web.HTTPError(404)
        self.render("register.html", **self.r_params)

    @multi_contest
    def post(self):
        if not self.contest.allow_registration:
            raise tornado.web.HTTPError(404)

        first_name = self.get_argument("first_name", "")
        last_name = self.get_argument("last_name", "")
        email = self.get_argument("email", "")
        role = self.get_argument("role", "")
        country = self.get_argument("country", "")
        district_id = self.get_argument("district", "")
        city = self.get_argument("city", "")
        school_id = self.get_argument("school", "")
        grade = self.get_argument("grade", None)

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

        if self.contest.require_country and not country:
            errors.append("country")

        if self.contest.require_school_details and not role:
            errors.append("role")

        if self.contest.require_school_details and role == "student":
            try:
                district_id = int(district_id)
            except ValueError:
                errors.append("district")
                district = None
            else:
                district = District.get_from_id(district_id, self.sql_session)
                if district is None:
                    errors.append("district")
            if not city:
                errors.append("city")
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
            try:
                grade = int(grade)
            except ValueError:
                errors.append("grade")
            else:
                if self.contest.allowed_grades:
                    if grade not in self.contest.allowed_grades:
                        errors.append("grade")
                else:
                    if not 1 <= grade <= 12:
                        errors.append("grade")
        else:
            district = None
            city = ""
            school = None
            grade = None

        if errors:
            self.render("register.html", errors=errors, **self.r_params)
            return

        password = build_password(self.generate_password())
        for _i in range(10):
            username = self.generate_username(first_name, last_name, email)
            if (self.sql_session.query(User)
                    .filter(User.username == username).count() == 0):
                break
        else:
            raise Exception  # TODO: show some error message

        # Everything's ok. Create the user and participation.
        # Set password on both.
        user = User(first_name=first_name, last_name=last_name, email=email,
                    username=username, password=password, country=country,
                    district=district, city=city, school=school, grade=grade)
        participation = Participation(contest=self.contest, user=user,
                                      password=password)
        self.sql_session.add(user)
        self.sql_session.add(participation)
        self.sql_session.commit()

        logger.info("New user registered from IP address %s, as user %r, on "
                    "contest %s, at %s", ip_address, username,
                    self.contest.name, self.timestamp)

        # TODO: send email

        method, password = parse_authentication(user.password)
        assert method == 'plaintext'
        self.render("register.html", new_user=user, password=password, **self.r_params)

    def generate_username(self, first_name, last_name, email):
        return "%s%s%04d" % (first_name[:3], last_name[:3],
                             random.randint(0, 9999))

    def generate_password(self):
        chars = "abcdefghijkmnopqrstuvwxyz23456789"
        return "".join(random.choice(chars)
                       for _i in range(8))


class StartHandler(ContestHandler):
    """Start handler.

    Used by a user who wants to start their per_user_time.

    """
    @tornado.web.authenticated
    @actual_phase_required(-1)
    @multi_contest
    def post(self):
        participation = self.current_user

        logger.info("Starting now for user %s", participation.user.username)
        participation.starting_time = self.timestamp
        self.sql_session.commit()

        self.redirect(self.contest_url())


class LogoutHandler(ContestHandler):
    """Logout handler.

    """
    @multi_contest
    def post(self):
        self.clear_cookie(self.contest.name + "_login")
        self.redirect(self.contest_url())


class ContestAttachmentViewHandler(FileHandler):
    """Shows an attachment file of a task in the contest.

    """
    @tornado.web.authenticated
    @actual_phase_required(0, 3)
    @multi_contest
    def get(self, filename):
        if filename not in self.contest.attachments:
            raise tornado.web.HTTPError(404)

        attachment = self.contest.attachments[filename].digest
        self.sql_session.close()

        mimetype = get_type_for_file_name(filename)
        if mimetype is None:
            mimetype = 'application/octet-stream'

        self.fetch(attachment, mimetype, filename)


class NotificationsHandler(ContestHandler):
    """Displays notifications.

    """

    refresh_cookie = False

    @tornado.web.authenticated
    @multi_contest
    def get(self):
        participation = self.current_user

        last_notification = self.get_argument("last_notification", None)
        if last_notification is not None:
            last_notification = make_datetime(float(last_notification))

        res = get_communications(self.sql_session, participation,
                                 self.timestamp, after=last_notification)

        # Simple notifications
        notifications = self.service.notifications
        username = participation.user.username
        if username in notifications:
            for notification in notifications[username]:
                res.append({"type": "notification",
                            "timestamp": make_timestamp(notification[0]),
                            "subject": notification[1],
                            "text": notification[2],
                            "level": notification[3]})
            del notifications[username]

        self.write(json.dumps(res))


class PrintingHandler(ContestHandler):
    """Serve the interface to print and handle submitted print jobs.

    """
    @tornado.web.authenticated
    @actual_phase_required(0)
    @multi_contest
    def get(self):
        participation = self.current_user

        if not self.r_params["printing_enabled"]:
            raise tornado.web.HTTPError(404)

        printjobs = self.sql_session.query(PrintJob)\
            .filter(PrintJob.participation == participation)\
            .all()

        remaining_jobs = max(0, config.max_jobs_per_user - len(printjobs))

        self.render("printing.html",
                    printjobs=printjobs,
                    remaining_jobs=remaining_jobs,
                    max_pages=config.max_pages_per_job,
                    pdf_printing_allowed=config.pdf_printing_allowed,
                    **self.r_params)

    @tornado.web.authenticated
    @actual_phase_required(0)
    @multi_contest
    def post(self):
        try:
            printjob = accept_print_job(
                self.sql_session, self.service.file_cacher, self.current_user,
                self.timestamp, self.request.files)
            self.sql_session.commit()
        except PrintingDisabled:
            raise tornado.web.HTTPError(404)
        except UnacceptablePrintJob as e:
            self.notify_error(e.subject, e.text, e.text_params)
        else:
            self.service.printing_service.new_printjob(printjob_id=printjob.id)
            self.notify_success(N_("Print job received"),
                                N_("Your print job has been received."))

        self.redirect(self.contest_url("printing"))


class DocumentationHandler(ContestHandler):
    """Displays the instruction (compilation lines, documentation,
    ...) of the contest.

    """
    @tornado.web.authenticated
    @multi_contest
    def get(self):
        self.render("documentation.html",
                    COMPILATION_MESSAGES=COMPILATION_MESSAGES,
                    EVALUATION_MESSAGES=EVALUATION_MESSAGES,
                    **self.r_params)
