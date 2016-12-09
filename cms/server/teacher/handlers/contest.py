#!/usr/bin/env python3

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2014-2020 Vytis Banaitis <vytis.banaitis@gmail.com>
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

try:
    import tornado4.web as tornado_web
except ImportError:
    import tornado.web as tornado_web
from sqlalchemy.orm import contains_eager, joinedload, subqueryload

from cms import config
from cms.db import Contest, Participation, User
from cms.grading.scoring import task_score
from cmscommon.datetime import make_timestamp

from .base import BaseHandler


logger = logging.getLogger(__name__)


def userattr(user):
    return getattr(user, config.teacher_login_kind)


class ContestHandler(BaseHandler):
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
        if int(contest_id) not in config.teacher_active_contests:
            raise tornado_web.HTTPError(404)
        contest = Contest.get_from_id(contest_id, self.sql_session)
        if contest is None:
            raise tornado_web.HTTPError(404)

        contest = self.sql_session.query(Contest)\
            .filter(Contest.id == contest.id)\
            .options(subqueryload('tasks'))\
            .options(joinedload('tasks.active_dataset'))\
            .one()

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
            self.r_params["header"] = header
            self.r_params["table"] = table
            self.r_params["allow_impersonate"] = config.teacher_allow_impersonate
            self.render("contest.html", **self.r_params)


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
        self.set_secure_cookie(p.contest.name + "_login",
                               json.dumps([p.user.username,
                                           password,
                                           make_timestamp(self.timestamp)]),
                               domain=domain,
                               expires_days=None)
        self.redirect(url)
