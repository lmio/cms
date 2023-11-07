#!/usr/bin/env python3

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2010-2014 Giovanni Mascellani <mascellani@poisson.phc.unipi.it>
# Copyright © 2010-2018 Stefano Maggiolo <s.maggiolo@gmail.com>
# Copyright © 2010-2012 Matteo Boscariol <boscarim@hotmail.com>
# Copyright © 2012-2014 Luca Wehrstedt <luca.wehrstedt@gmail.com>
# Copyright © 2013 Bernard Blackham <bernard@largestprime.net>
# Copyright © 2014 Artem Iglikov <artem.iglikov@gmail.com>
# Copyright © 2014 Fabian Gundlach <320pointsguy@gmail.com>
# Copyright © 2014-2024 Vytis Banaitis <vytis.banaitis@gmail.com>
# Copyright © 2015-2018 William Di Luigi <williamdiluigi@gmail.com>
# Copyright © 2021 Grace Hawkins <amoomajid99@gmail.com>
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

import ipaddress
import json
import logging
import random
import re

try:
    import tornado4.web as tornado_web
except ImportError:
    import tornado.web as tornado_web
from sqlalchemy.orm import subqueryload
from sqlalchemy.orm.exc import NoResultFound
from unidecode import unidecode

from cms import config
from cms.db import PrintJob, User, Participation, Team, District, School
from cms.grading.steps import COMPILATION_MESSAGES, EVALUATION_MESSAGES
from cms.server import multi_contest
from cms.server.contest.authentication import validate_login
from cms.server.contest.communication import get_communications
from cms.server.contest.printing import accept_print_job, PrintingDisabled, \
    UnacceptablePrintJob
from cms.util import lt_sort_key
from cmscommon.crypto import hash_password, validate_password, generate_random_password
from cmscommon.datetime import make_datetime, make_timestamp
from cmscommon.mimetypes import get_type_for_file_name
from .contest import ContestHandler, FileHandler
from ..phase_management import actual_phase_required


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


class RegistrationHandler(ContestHandler):
    """Registration handler.

    Used to create a participation when this is allowed.
    If `new_user` argument is true, it creates a new user too.

    """

    MAX_INPUT_LENGTH = 50
    MIN_PASSWORD_LENGTH = 6
    email_re = re.compile(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")

    def render_params(self):
        params = super().render_params()

        params["MAX_INPUT_LENGTH"] = self.MAX_INPUT_LENGTH
        params["MIN_PASSWORD_LENGTH"] = self.MIN_PASSWORD_LENGTH
        if self.contest.registration_require_team:
            params["teams"] = self.sql_session.query(Team)\
                                  .order_by(Team.name).all()

        if self.contest.registration_require_school_details:
            district_list = (self.sql_session.query(District)
                             .options(subqueryload(District.schools))
                             .all())
            district_list.sort(key=lambda d: lt_sort_key(d.name))
            for d in district_list:
                d.schools.sort(key=lambda s: lt_sort_key(s.name))
            params["district_list"] = district_list

        params["policy_url"] = config.data_management_policy_url
        return params

    @multi_contest
    def get(self):
        if not self.contest.allow_registration:
            raise tornado_web.HTTPError(404)
        self.render("register.html", **self.r_params)

    @multi_contest
    def post(self):
        if not self.contest.allow_registration:
            raise tornado_web.HTTPError(404)

        try:
            ip_address = ipaddress.ip_address(self.request.remote_ip)
        except ValueError:
            logger.warning("Invalid IP address provided by Tornado: %s",
                           self.request.remote_ip)
            return None

        user, password = self.do_register()

        logger.info("New user registered from IP address %s, as user %r, on "
                    "contest %s, at %s", ip_address, user.username,
                    self.contest.name, self.timestamp)

        if password is not None:
            resp = f"{user.username}:{password}"
        else:
            resp = user.username
        self.finish(resp)

    def do_register(self, require_registered_by=False):
        if config.data_management_policy_url:
            accept_terms = self.get_argument("accept_terms", None)
            if accept_terms != 'yes':
                raise tornado_web.HTTPError(400)

        create_new_user = self.get_argument("new_user") == "true"

        # Get or create user
        if create_new_user:
            user, password = self._create_user(require_registered_by=require_registered_by)
        else:
            if not self.contest.registration_allow_join:
                raise tornado_web.HTTPError(400)

            user = self._get_user()
            password = None

            # Check if the participation exists
            contest = self.contest
            tot_participants = self.sql_session.query(Participation)\
                                   .filter(Participation.user == user)\
                                   .filter(Participation.contest == contest)\
                                   .count()
            if tot_participants > 0:
                raise tornado_web.HTTPError(409)

        # Create participation
        team = self._get_team()
        participation = Participation(user=user, contest=self.contest,
                                      team=team)
        self.sql_session.add(participation)

        self.sql_session.commit()

        return user, password

    def _create_user(self, require_registered_by=False):
        try:
            first_name = self.get_argument("first_name")
            last_name = self.get_argument("last_name")
            email = self.get_argument("email")

            if not 1 <= len(first_name) <= self.MAX_INPUT_LENGTH:
                raise ValueError()
            if not 1 <= len(last_name) <= self.MAX_INPUT_LENGTH:
                raise ValueError()
            if not 1 <= len(email) <= self.MAX_INPUT_LENGTH \
                    or not self.email_re.match(email):
                raise ValueError()

            if self.contest.registration_require_country:
                country = self.get_argument("country")

                if not 1 <= len(country) <= self.MAX_INPUT_LENGTH:
                    raise ValueError()

            else:
                country = None

            if self.contest.registration_require_school_details \
                    and self.get_argument("role") == 'student':
                district_id = self.get_argument("district")
                city = self.get_argument("city")
                school_id = self.get_argument("school")
                grade = self.get_argument("grade")

                district_id = int(district_id)
                district = District.get_from_id(district_id, self.sql_session)
                if district is None:
                    raise ValueError()
                if not 1 <= len(city) <= self.MAX_INPUT_LENGTH:
                    raise ValueError()
                school_id = int(school_id)
                school = School.get_from_id(school_id, self.sql_session)
                if school is None:
                    raise ValueError()
                if school.district != district:
                    raise ValueError()
                grade = int(grade)
                if self.contest.registration_allowed_grades:
                    if grade not in self.contest.registration_allowed_grades:
                        raise ValueError()
                else:
                    if not 1 <= grade <= 12:
                        raise ValueError()
            else:
                district = city = school = grade = None

            if self.contest.registration_auto_credentials:
                username = self._generate_username(first_name, last_name)
                password = generate_random_password()
            else:
                username = self.get_argument("username")
                password = self.get_argument("password")

                if not 1 <= len(username) <= self.MAX_INPUT_LENGTH:
                    raise ValueError()
                if not re.match(r"^[A-Za-z0-9_-]+$", username):
                    raise ValueError()
                if not self.MIN_PASSWORD_LENGTH <= len(password) \
                        <= self.MAX_INPUT_LENGTH:
                    raise ValueError()

            if require_registered_by:
                registered_by = self.get_argument("registered_by")
                if not 1 <= len(registered_by) <= self.MAX_INPUT_LENGTH:
                    raise ValueError()
            else:
                registered_by = None

        except (tornado_web.MissingArgumentError, ValueError):
            raise tornado_web.HTTPError(400)

        if self.contest.registration_auto_credentials:
            hash_method = 'plaintext'
            ret_password = password
        else:
            hash_method = 'bcrypt'
            ret_password = None
        # Override password with its hash
        password = hash_password(password, hash_method)

        # Check if the username is available
        tot_users = self.sql_session.query(User)\
                        .filter(User.username == username).count()
        if tot_users != 0:
            # HTTP 409: Conflict
            raise tornado_web.HTTPError(409)

        # Store new user
        user = User(first_name, last_name, username, password, email=email,
                    country=country, district=district, city=city,
                    school=school, grade=grade, registered_by=registered_by,
                    registration_timestamp=self.timestamp)
        self.sql_session.add(user)

        return user, ret_password

    def _generate_username(self, first_name, last_name):
        prefix = f"{self._to_ascii(first_name)[:3]}{self._to_ascii(last_name)[:3]}"
        for _i in range(10):
            username = f"{prefix}{random.randint(0, 9999):04d}"
            if (self.sql_session.query(User)
                    .filter(User.username == username).count() == 0):
                return username
        else:
            raise ValueError

    def _to_ascii(self, value):
        return "".join(re.findall(r"[A-Za-z0-9_-]+", unidecode(value)))

    def _get_user(self):
        username = self.get_argument("username")
        password = self.get_argument("password")

        # Find user if it exists
        user = self.sql_session.query(User)\
                        .filter(User.username == username)\
                        .first()
        if user is None:
            raise tornado_web.HTTPError(404)

        # Check if password is correct
        if not validate_password(user.password, password):
            raise tornado_web.HTTPError(403)

        return user

    def _get_team(self):
        if self.contest.registration_require_team:
            try:
                team_code = self.get_argument("team")
                team = self.sql_session.query(Team)\
                           .filter(Team.code == team_code)\
                           .one()
            except (tornado_web.MissingArgumentError, NoResultFound):
                raise tornado_web.HTTPError(400)
        else:
            team = None

        return team


class RegistrationByParentHandler(RegistrationHandler):
    @multi_contest
    def get(self):
        if not self.contest.allow_registration_by_parent:
            raise tornado_web.HTTPError(404)
        self.render("register_by_parent.html", **self.r_params)

    @multi_contest
    def post(self):
        if not self.contest.allow_registration_by_parent:
            raise tornado_web.HTTPError(404)

        try:
            ip_address = ipaddress.ip_address(self.request.remote_ip)
        except ValueError:
            logger.warning("Invalid IP address provided by Tornado: %s",
                           self.request.remote_ip)
            return None

        user, _password = self.do_register(require_registered_by=True)

        logger.info("New user registered by parent from IP address %s, as "
                    "user %r, on contest %s, at %s", ip_address, user.username,
                    self.contest.name, self.timestamp)

        if self.contest.registration_auto_credentials:
            self.finish("ok")
        else:
            self.finish(user.username)


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
            ip_address = ipaddress.ip_address(self.request.remote_ip)
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


class StartHandler(ContestHandler):
    """Start handler.

    Used by a user who wants to start their per_user_time.

    """
    @tornado_web.authenticated
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
    @tornado_web.authenticated
    @actual_phase_required(0, 3)
    @multi_contest
    def get(self, filename):
        if filename not in self.contest.attachments:
            raise tornado_web.HTTPError(404)

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

    @tornado_web.authenticated
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
    @tornado_web.authenticated
    @actual_phase_required(0)
    @multi_contest
    def get(self):
        participation = self.current_user

        if not self.r_params["printing_enabled"]:
            raise tornado_web.HTTPError(404)

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

    @tornado_web.authenticated
    @actual_phase_required(0)
    @multi_contest
    def post(self):
        try:
            printjob = accept_print_job(
                self.sql_session, self.service.file_cacher, self.current_user,
                self.timestamp, self.request.files)
            self.sql_session.commit()
        except PrintingDisabled:
            raise tornado_web.HTTPError(404)
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
    @tornado_web.authenticated
    @multi_contest
    def get(self):
        self.render("documentation.html",
                    COMPILATION_MESSAGES=COMPILATION_MESSAGES,
                    EVALUATION_MESSAGES=EVALUATION_MESSAGES,
                    **self.r_params)
