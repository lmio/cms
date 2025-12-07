#!/usr/bin/env python3

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2014-2024 Vytis Banaitis <vytis.banaitis@gmail.com>
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

"""Contest handler classes for TWS.

"""

import csv
import ipaddress
import json
import logging
from urllib.parse import urlparse

import collections
try:
    collections.MutableMapping
except:
    # Monkey-patch: Tornado 4.5.3 does not work on Python 3.11 by default
    collections.MutableMapping = collections.abc.MutableMapping

try:
    import tornado4.web as tornado_web
except ImportError:
    import tornado.web as tornado_web
from sqlalchemy.orm import contains_eager, joinedload, subqueryload

from cms import config, PARTICIPATION_LOCATION_ONSITE, PARTICIPATION_LOCATION_REMOTE
from cms.db import Contest, Participation, Task, User, DistrictSubmissionArchive
from cms.grading.scoring import task_score
from cms.server import FileHandlerMixin
from cms.server.contest.handlers.base import BaseHandler as CWSBaseHandler
from cmscommon.datetime import make_timestamp
from cmscommon.mimetypes import get_type_for_file_name

from .base import BaseHandler


logger = logging.getLogger(__name__)


def userattr(user):
    return getattr(user, config.teacher_login_kind)


class BaseContestHandler(BaseHandler):
    """Base handler for contest-related handlers.

    """
    def get_contest(self, contest_id):
        if int(contest_id) not in config.teacher_active_contests:
            raise tornado_web.HTTPError(404)
        contest = Contest.get_from_id(contest_id, self.sql_session)
        if contest is None:
            raise tornado_web.HTTPError(404)
        return contest

    def should_show_task_statements(self, contest):
        if config.teacher_show_task_statements == 'always':
            return True
        elif config.teacher_show_task_statements == 'after_start':
            return contest.phase(self.timestamp) >= 0
        else:
            return False


class ContestFileHandler(BaseContestHandler, FileHandlerMixin):
    pass


class ContestHandler(BaseContestHandler):
    """Contest result list handler.

    """
    def get_results_table(self, contest, participations):
        show_results = config.teacher_show_results and contest.phase(self.timestamp) >= 0

        header = [
            self._("Username"),
            self._("Contestant"),
            self._("School"),
            self._("Grade"),
        ]
        if show_results:
            for task in contest.tasks:
                header.append(task.name)
            header.append(self._("Total"))

        table = []
        for p in sorted(participations, key=lambda p: p.user.username):
            if p.hidden:
                continue
            row = [
                p.user.username,
                "{} {}".format(p.user.first_name, p.user.last_name),
                p.user.school.name if p.user.school else "",
                p.user.grade if p.user.grade else "",
            ]
            if show_results:
                score = 0.0
                partial = False
                for task in contest.tasks:
                    t_score, t_partial = task_score(p, task, rounded=True)
                    score += t_score
                    partial = partial or t_partial
                    row.append("{}{}".format(t_score, "*" if t_partial else ""))
                score = round(score, contest.score_precision)
                row.append("{}{}".format(score, "*" if partial else ""))
            table.append((p, row))

        return header, table

    @tornado_web.authenticated
    def get(self, contest_id, format="online"):
        contest = self.get_contest(contest_id)

        show_task_statements = format == 'online' and self.should_show_task_statements(contest)

        contest_query = self.sql_session.query(Contest)\
            .filter(Contest.id == contest.id)\
            .options(subqueryload('tasks'))\
            .options(joinedload('tasks.active_dataset'))
        if show_task_statements:
            contest_query = contest_query\
                .options(subqueryload('tasks.statements'))\
                .options(subqueryload('tasks.attachments'))\
                .options(subqueryload('attachments'))
        contest = contest_query.one()

        participations = self.sql_session.query(Participation)\
            .join(Participation.user)\
            .filter(Participation.contest == contest)\
            .filter(userattr(User) == self.current_user)\
            .options(contains_eager('user'))\
            .options(joinedload('user.school'))\
            .options(subqueryload('submissions'))\
            .options(subqueryload('submissions.token'))\
            .options(subqueryload('submissions.results'))\
            .all()

        header, table = self.get_results_table(contest, participations)

        if format == "csv":
            self.set_header("Content-Type", "text/csv")
            self.set_header("Content-Disposition",
                            "attachment; filename=\"results.csv\"")

            writer = csv.writer(self)
            writer.writerow(header)
            writer.writerows(row for user, row in table)
            self.finish()
        else:
            self.r_params["contest"] = contest
            self.r_params["show_task_statements"] = show_task_statements
            self.r_params["submission_archive"] = (
                config.teacher_login_kind == "district"
                and (
                    self.sql_session.query(DistrictSubmissionArchive)
                    .filter(
                        DistrictSubmissionArchive.district_id == self.current_user.id,
                        DistrictSubmissionArchive.contest_id == contest.id,
                    ).first() is not None
                )
            )
            self.r_params["header"] = header
            self.r_params["table"] = table
            self.r_params["allow_impersonate"] = config.teacher_allow_impersonate
            self.r_params["enable_participation_location"] = (
                config.teacher_enable_participation_locations
            )
            self.r_params["enable_participation_location_edit"] = (
                config.teacher_enable_participation_locations and
                contest.phase(self.timestamp) <= 0
            )
            self.r_params["allow_contestant_leave"] = (
                config.teacher_allow_contestant_leave and
                contest.phase(self.timestamp) == 0
            )
            self.render("contest.html", **self.r_params)


class TaskStatementHandler(ContestFileHandler):
    """Shows the statement file of a task in the contest.

    """
    @tornado_web.authenticated
    def get(self, contest_id, task_name, lang_code):
        contest = self.get_contest(contest_id)
        if not self.should_show_task_statements(contest):
            raise tornado_web.HTTPError(404)

        task = self.sql_session.query(Task)\
            .filter(Task.contest == contest)\
            .filter(Task.name == task_name)\
            .one_or_none()
        if task is None:
            raise tornado_web.HTTPError(404)
        if lang_code not in task.statements:
            raise tornado_web.HTTPError(404)

        statement = task.statements[lang_code].digest
        self.sql_session.close()

        filename = "%s (%s).pdf" % (task.name, lang_code)

        self.fetch(statement, "application/pdf", filename)


class TaskAttachmentHandler(ContestFileHandler):
    """Shows an attachment file of a task in the contest.

    """
    @tornado_web.authenticated
    def get(self, contest_id, task_name, filename):
        contest = self.get_contest(contest_id)
        if not self.should_show_task_statements(contest):
            raise tornado_web.HTTPError(404)

        task = self.sql_session.query(Task)\
            .filter(Task.contest == contest)\
            .filter(Task.name == task_name)\
            .one_or_none()
        if task is None:
            raise tornado_web.HTTPError(404)
        if filename not in task.attachments:
            raise tornado_web.HTTPError(404)

        attachment = task.attachments[filename].digest
        self.sql_session.close()

        mimetype = get_type_for_file_name(filename)
        if mimetype is None:
            mimetype = 'application/octet-stream'

        self.fetch(attachment, mimetype, filename)


class ContestAttachmentHandler(ContestFileHandler):
    """Shows an attachment file of the contest.

    """
    @tornado_web.authenticated
    def get(self, contest_id, filename):
        contest = self.get_contest(contest_id)
        if not self.should_show_task_statements(contest):
            raise tornado_web.HTTPError(404)

        if filename not in contest.attachments:
            raise tornado_web.HTTPError(404)

        attachment = contest.attachments[filename].digest
        self.sql_session.close()

        mimetype = get_type_for_file_name(filename)
        if mimetype is None:
            mimetype = 'application/octet-stream'

        self.fetch(attachment, mimetype, filename)


class ContestantLocationHandler(BaseHandler):
    """Set contestant participation location.

    """
    @tornado_web.authenticated
    def post(self, participation_id):
        if not config.teacher_enable_participation_locations:
            raise tornado_web.HTTPError(403)

        p = Participation.get_from_id(participation_id, self.sql_session)
        if p is None:
            raise tornado_web.HTTPError(404)
        if (p.contest_id not in config.teacher_active_contests or
                userattr(p.user) != self.current_user):
            raise tornado_web.HTTPError(403)

        return_url = self.url("contest", p.contest.id)

        if p.contest.phase(self.timestamp) > 0:
            return self.redirect(return_url)

        location = self.get_argument("location", "")
        if location not in (PARTICIPATION_LOCATION_ONSITE, PARTICIPATION_LOCATION_REMOTE):
            raise tornado_web.HTTPError(400)

        try:
            ip_address = ipaddress.ip_address(self.request.remote_ip)
        except ValueError:
            logger.warning("Invalid IP address provided by Tornado: %s",
                           self.request.remote_ip)
            return None

        p.location = location
        logger.info("Teacher set location to %s for contestant %r on contest %s, "
                    "from IP address %s, at %s.",
                    location, p.user.username, p.contest.name, ip_address,
                    self.timestamp)

        self.sql_session.commit()

        return self.redirect(return_url)


class ContestantLeaveHandler(BaseHandler):
    """Set or reset contestant leave time.

    """
    @tornado_web.authenticated
    def post(self, participation_id):
        if not config.teacher_allow_contestant_leave:
            raise tornado_web.HTTPError(403)

        p = Participation.get_from_id(participation_id, self.sql_session)
        if p is None:
            raise tornado_web.HTTPError(404)
        if (p.contest_id not in config.teacher_active_contests or
                userattr(p.user) != self.current_user):
            raise tornado_web.HTTPError(403)

        return_url = self.url("contest", p.contest.id)

        if p.contest.phase(self.timestamp) != 0:
            return self.redirect(return_url)

        state = self.get_argument("state", "")

        try:
            ip_address = ipaddress.ip_address(self.request.remote_ip)
        except ValueError:
            logger.warning("Invalid IP address provided by Tornado: %s",
                           self.request.remote_ip)
            return None

        if state == "left":
            if p.leave_time is None or p.leave_time > self.timestamp:
                p.leave_time = self.timestamp
                logger.info("Teacher set contestant %r on contest %s as left, "
                            "from IP address %s, at %s.",
                            p.user.username, p.contest.name, ip_address,
                            self.timestamp)
        elif state == "returned":
            if p.leave_time is not None:
                p.leave_time = None
                logger.info("Teacher set contestant %r on contest %s as returned, "
                            "from IP address %s, at %s.",
                            p.user.username, p.contest.name, ip_address,
                            self.timestamp)
        else:
            raise tornado_web.HTTPError(400)

        self.sql_session.commit()

        return self.redirect(return_url)


class ImpersonateHandler(BaseHandler):
    """Impersonate a contestant.

    """
    @tornado_web.authenticated
    def get(self, participation_id):
        if not config.teacher_allow_impersonate:
            raise tornado_web.HTTPError(403)

        p = Participation.get_from_id(participation_id, self.sql_session)
        if p is None:
            raise tornado_web.HTTPError(404)
        if (p.contest_id not in config.teacher_active_contests or
                userattr(p.user) != self.current_user):
            raise tornado_web.HTTPError(403)

        url = self.service.contest_url[p.contest_id]
        domain = urlparse(url).hostname

        try:
            ip_address = ipaddress.ip_address(self.request.remote_ip)
        except ValueError:
            logger.warning("Invalid IP address provided by Tornado: %s",
                           self.request.remote_ip)
            return None

        logger.info("Teacher logged in as contestant from IP address %s, as "
                    "user %r, on contest %s, at %s.", ip_address,
                    p.user.username, p.contest.name, self.timestamp)
        password = p.password if p.password is not None else p.user.password
        self.set_secure_cookie(CWSBaseHandler.LOGIN_COOKIE_NAME,
                               json.dumps([p.user.username,
                                           password,
                                           make_timestamp(self.timestamp)]),
                               domain=domain,
                               expires_days=None)
        self.redirect(url)


class SubmissionArchiveHandler(ContestFileHandler):
    """Serve the district's submissions archive.

    """
    @tornado_web.authenticated
    def get(self, contest_id):
        if config.teacher_login_kind != "district":
            raise tornado_web.HTTPError(404)

        contest = self.get_contest(contest_id)
        archive = (
            self.sql_session.query(DistrictSubmissionArchive)
            .filter(
                DistrictSubmissionArchive.district_id == self.current_user.id,
                DistrictSubmissionArchive.contest_id == contest.id,
            )
            .first()
        )
        if archive is None:
            raise tornado_web.HTTPError(404)

        digest = archive.digest
        self.sql_session.close()

        self.fetch(digest, "application/zip", "submissions.zip")
