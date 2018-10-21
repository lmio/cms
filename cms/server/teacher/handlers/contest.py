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

import csv
import json
import logging
import urlparse

import tornado.web

from sqlalchemy.orm import joinedload

from cms import config
from cms.db import Contest, Participation, User
from cms.grading import task_score
from cms.server import CommonRequestHandler, filter_ascii
from cmscommon.datetime import make_timestamp

from .base import BaseHandler


logger = logging.getLogger(__name__)


def userattr(user):
    return getattr(user, config.teacher_login_kind)


class ContestHandler(BaseHandler):
    """Contest result list handler.

    """
    def get_results_table(self, contest, participations):
        header = [
            self._("Username"),
            self._("Contestant"),
            self._("School"),
            self._("Grade"),
        ]
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
            for task in contest.tasks:
                t_score, t_partial = task_score(p, task)
                t_score = round(t_score, task.score_precision)
                score += t_score
                partial = partial or t_partial
                row.append("{}{}".format(t_score, "*" if t_partial else ""))
            score = round(score, contest.score_precision)
            row.append("{}{}".format(score, "*" if partial else ""))
            table.append((p, row))

        return header, table

    @tornado.web.authenticated
    def get(self, contest_id, format="online"):
        if int(contest_id) not in config.teacher_active_contests:
            raise tornado.web.HTTPError(404)
        contest = Contest.get_from_id(contest_id, self.sql_session)
        if contest is None:
            raise tornado.web.HTTPError(404)

        participations = self.sql_session.query(Participation)\
            .join(Participation.user)\
            .filter(Participation.contest == contest)\
            .filter(userattr(User) == self.current_user)\
            .options(joinedload('user.school'))\
            .options(joinedload('submissions'))\
            .options(joinedload('submissions.token'))\
            .options(joinedload('submissions.results'))\
            .all()

        header, table = self.get_results_table(contest, participations)

        if format == "csv":
            self.set_header("Content-Type", "text/csv")
            self.set_header("Content-Disposition",
                            "attachment; filename=\"results.csv\"")

            def encode(row):
                return [unicode(item).encode('utf-8') for item in row]

            writer = csv.writer(self)
            writer.writerow(encode(header))
            writer.writerows(encode(row) for user, row in table)
            self.finish()
        else:
            self.r_params["contest"] = contest
            self.r_params["header"] = header
            self.r_params["table"] = table
            self.render("contest.html", **self.r_params)


class ImpersonateHandler(BaseHandler):
    """Impersonate a contestant.

    """
    @tornado.web.authenticated
    def get(self, participation_id):
        p = Participation.get_from_id(participation_id, self.sql_session)
        if p is None:
            raise tornado.web.HTTPError(404)
        if (p.contest_id not in config.teacher_active_contests or
                userattr(p.user) != self.current_user):
            raise tornado.web.HTTPError(403)

        url = self.application.service.contest_url[p.contest_id]
        domain = urlparse.urlparse(url).hostname

        filtered_username = filter_ascii(p.user.username)
        logger.info("Teacher logged in as contestant: username=%s remote_ip=%s." %
                    (filtered_username, self.request.remote_ip))
        password = p.password if p.password is not None else p.user.password
        self.set_secure_cookie("login",
                               json.dumps([p.user.username,
                                           password,
                                           make_timestamp()]),
                               domain=domain,
                               expires_days=None)
        # Bypass the overriden redirect because we are going outside
        # this web server.
        super(CommonRequestHandler, self).redirect(url)
