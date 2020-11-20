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
from future.moves.urllib.parse import urlparse
import six

import csv
import ipaddress
import json
import logging

import tornado.web

from sqlalchemy.orm import contains_eager, joinedload, subqueryload

from cms import config
from cms.db import Contest, Participation, Task, User
from cms.grading.scoring import task_score
from cms.server import CommonRequestHandler, FileHandlerMixin
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
            raise tornado.web.HTTPError(404)
        contest = Contest.get_from_id(contest_id, self.sql_session)
        if contest is None:
            raise tornado.web.HTTPError(404)
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
            score = 0.0
            partial = False
            row = [
                p.user.username,
                "{} {}".format(p.user.first_name, p.user.last_name),
                p.user.school.name if p.user.school else "",
                p.user.grade if p.user.grade else "",
            ]
            if show_results:
                for task in contest.tasks:
                    t_score, t_partial = task_score(p, task, rounded=True)
                    score += t_score
                    partial = partial or t_partial
                    row.append("{}{}".format(t_score, "*" if t_partial else ""))
                score = round(score, contest.score_precision)
                row.append("{}{}".format(score, "*" if partial else ""))
            table.append((p, row))

        return header, table

    @tornado.web.authenticated
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

            if six.PY3:
                def encode(row):
                    return [str(item) for item in row]
            else:
                def encode(row):
                    return [str(item).encode('utf-8') for item in row]

            writer = csv.writer(self)
            writer.writerow(encode(header))
            writer.writerows(encode(row) for user, row in table)
            self.finish()
        else:
            self.r_params["contest"] = contest
            self.r_params["show_task_statements"] = show_task_statements
            self.r_params["header"] = header
            self.r_params["table"] = table
            self.r_params["allow_impersonate"] = config.teacher_allow_impersonate
            self.r_params["allow_contestant_leave"] = (
                config.teacher_allow_contestant_leave and
                contest.phase(self.timestamp) == 0
            )
            self.render("contest.html", **self.r_params)


class TaskStatementHandler(ContestFileHandler):
    """Shows the statement file of a task in the contest.

    """
    @tornado.web.authenticated
    def get(self, contest_id, task_name, lang_code):
        contest = self.get_contest(contest_id)
        if not self.should_show_task_statements(contest):
            raise tornado.web.HTTPError(404)

        task = self.sql_session.query(Task)\
            .filter(Task.contest == contest)\
            .filter(Task.name == task_name)\
            .one_or_none()
        if task is None:
            raise tornado.web.HTTPError(404)
        if lang_code not in task.statements:
            raise tornado.web.HTTPError(404)

        statement = task.statements[lang_code].digest
        self.sql_session.close()

        filename = "%s (%s).pdf" % (task.name, lang_code)

        self.fetch(statement, "application/pdf", filename)


class TaskAttachmentHandler(ContestFileHandler):
    """Shows an attachment file of a task in the contest.

    """
    @tornado.web.authenticated
    def get(self, contest_id, task_name, filename):
        contest = self.get_contest(contest_id)
        if not self.should_show_task_statements(contest):
            raise tornado.web.HTTPError(404)

        task = self.sql_session.query(Task)\
            .filter(Task.contest == contest)\
            .filter(Task.name == task_name)\
            .one_or_none()
        if task is None:
            raise tornado.web.HTTPError(404)
        if filename not in task.attachments:
            raise tornado.web.HTTPError(404)

        attachment = task.attachments[filename].digest
        self.sql_session.close()

        mimetype = get_type_for_file_name(filename)
        if mimetype is None:
            mimetype = 'application/octet-stream'

        self.fetch(attachment, mimetype, filename)


class ContestAttachmentHandler(ContestFileHandler):
    """Shows an attachment file of the contest.

    """
    @tornado.web.authenticated
    def get(self, contest_id, filename):
        contest = self.get_contest(contest_id)
        if not self.should_show_task_statements(contest):
            raise tornado.web.HTTPError(404)

        if filename not in contest.attachments:
            raise tornado.web.HTTPError(404)

        attachment = contest.attachments[filename].digest
        self.sql_session.close()

        mimetype = get_type_for_file_name(filename)
        if mimetype is None:
            mimetype = 'application/octet-stream'

        self.fetch(attachment, mimetype, filename)


class ContestantLeaveHandler(BaseHandler):
    """Set or reset contestant leave time.

    """
    @tornado.web.authenticated
    def post(self, participation_id):
        if not config.teacher_allow_contestant_leave:
            raise tornado.web.HTTPError(403)

        p = Participation.get_from_id(participation_id, self.sql_session)
        if p is None:
            raise tornado.web.HTTPError(404)
        if (p.contest_id not in config.teacher_active_contests or
                userattr(p.user) != self.current_user):
            raise tornado.web.HTTPError(403)

        return_url = self.url("contest", p.contest.id)

        if p.contest.phase(self.timestamp) != 0:
            return self.redirect(return_url)

        state = self.get_argument("state", "")

        try:
            # In py2 Tornado gives us the IP address as a native binary
            # string, whereas ipaddress wants text (unicode) strings.
            ip_address = ipaddress.ip_address(str(self.request.remote_ip))
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
            raise tornado.web.HTTPError(400)

        self.sql_session.commit()

        return self.redirect(return_url)


class ImpersonateHandler(BaseHandler):
    """Impersonate a contestant.

    """
    @tornado.web.authenticated
    def get(self, participation_id):
        if not config.teacher_allow_impersonate:
            raise tornado.web.HTTPError(403)

        p = Participation.get_from_id(participation_id, self.sql_session)
        if p is None:
            raise tornado.web.HTTPError(404)
        if (p.contest_id not in config.teacher_active_contests or
                userattr(p.user) != self.current_user):
            raise tornado.web.HTTPError(403)

        url = self.service.contest_url[p.contest_id]
        domain = urlparse(url).hostname

        try:
            # In py2 Tornado gives us the IP address as a native binary
            # string, whereas ipaddress wants text (unicode) strings.
            ip_address = ipaddress.ip_address(str(self.request.remote_ip))
        except ValueError:
            logger.warning("Invalid IP address provided by Tornado: %s",
                           self.request.remote_ip)
            return None

        logger.info("Teacher logged in as contestant from IP address %s, as "
                    "user %r, on contest %s, at %s.", ip_address,
                    p.user.username, p.contest.name, self.timestamp)
        password = p.password if p.password is not None else p.user.password
        self.set_secure_cookie(p.contest.name + "_login",
                               json.dumps([p.user.username,
                                           password,
                                           make_timestamp(self.timestamp)]),
                               domain=domain,
                               expires_days=None)
        # Bypass the overridden redirect because we are going outside
        # this web server.
        super(CommonRequestHandler, self).redirect(url)
