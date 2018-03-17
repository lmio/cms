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

"""Contest-related handlers for AWS.

"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import csv

from sqlalchemy.orm import joinedload

from cms.db import District, School, TeacherRegistration
from cmscommon.datetime import make_datetime

from .base import BaseHandler, require_permission


class DistrictListHandler(BaseHandler):
    """Displays the list of districts.

    """
    @require_permission(BaseHandler.AUTHENTICATED)
    def get(self):
        self.r_params = self.render_params()
        self.r_params["district_list"] = self.sql_session.query(District).all()
        self.render("districtlist.html", **self.r_params)


class DistrictHandler(BaseHandler):
    """Displays and allows to edit a district.

    """
    @require_permission(BaseHandler.AUTHENTICATED)
    def get(self, district_id):
        district = self.safe_get_item(District, district_id)

        self.r_params = self.render_params()
        self.r_params["district"] = district
        self.render("district.html", **self.r_params)

    @require_permission(BaseHandler.PERMISSION_ALL)
    def post(self, district_id):
        district = self.safe_get_item(District, district_id)

        try:
            attrs = district.get_attrs()

            self.get_string(attrs, "name", empty=None)
            self.get_string(attrs, "password")

            assert attrs.get("name") is not None, "No district name specified."

            # Update the district.
            district.set_attrs(attrs)

        except Exception as error:
            self.application.service.add_notification(
                make_datetime(), "Invalid field(s).", repr(error))
            self.redirect("/district/%s" % district_id)
            return

        if self.try_commit():
            pass
        self.redirect("/district/%s" % district_id)


class AddDistrictHandler(BaseHandler):
    """Adds a new district.

    """
    @require_permission(BaseHandler.PERMISSION_ALL)
    def get(self):
        self.r_params = self.render_params()
        self.render("add_district.html", **self.r_params)

    @require_permission(BaseHandler.PERMISSION_ALL)
    def post(self):
        try:
            attrs = dict()

            self.get_string(attrs, "name", empty=None)
            self.get_string(attrs, "password")

            assert attrs.get("name") is not None, "No district name specified."

            # Create the district.
            district = District(**attrs)
            self.sql_session.add(district)

        except Exception as error:
            self.application.service.add_notification(
                make_datetime(), "Invalid field(s).", repr(error))
            self.redirect("/district/add")
            return

        if self.try_commit():
            self.redirect("/district/%s" % district.id)
        else:
            self.redirect("/district/add")


class SchoolHandler(BaseHandler):
    """Displays and allows to edit a school.

    """
    @require_permission(BaseHandler.AUTHENTICATED)
    def get(self, school_id):
        school = self.safe_get_item(School, school_id)

        self.r_params = self.render_params()
        self.r_params["school"] = school
        self.r_params["district_list"] = self.sql_session.query(District).all()
        self.render("school.html", **self.r_params)

    @require_permission(BaseHandler.PERMISSION_ALL)
    def post(self, school_id):
        school = self.safe_get_item(School, school_id)

        try:
            attrs = school.get_attrs()

            self.get_int(attrs, "district")
            assert attrs.get("district") is not None, "No district selected."
            attrs["district"] = District.get_from_id(attrs["district"], self.sql_session)

            self.get_string(attrs, "name", empty=None)
            self.get_string(attrs, "password")

            assert attrs.get("name") is not None, "No school name specified."

            # Update the school.
            school.set_attrs(attrs)

        except Exception as error:
            self.application.service.add_notification(
                make_datetime(), "Invalid field(s).", repr(error))
            self.redirect("/school/%s" % school_id)
            return

        if self.try_commit():
            pass
        self.redirect("/school/%s" % school_id)


class AddSchoolHandler(BaseHandler):
    """Adds a new school.

    """
    @require_permission(BaseHandler.PERMISSION_ALL)
    def get(self, district_id):
        district = self.safe_get_item(District, district_id)

        self.r_params = self.render_params()
        self.r_params["district"] = district
        self.render("add_school.html", **self.r_params)

    @require_permission(BaseHandler.PERMISSION_ALL)
    def post(self, district_id):
        district = self.safe_get_item(District, district_id)

        try:
            attrs = dict()

            self.get_string(attrs, "name", empty=None)
            self.get_string(attrs, "password")

            assert attrs.get("name") is not None, "No school name specified."

            # Create the school.
            attrs["district"] = district
            school = School(**attrs)
            self.sql_session.add(school)

        except Exception as error:
            self.application.service.add_notification(
                make_datetime(), "Invalid field(s).", repr(error))
            self.redirect("/school/add/%s" % district.id)
            return

        if self.try_commit():
            self.redirect("/school/%s" % school.id)
        else:
            self.redirect("/school/add/%s" % district.id)


class TeacherRegistrationsHandler(BaseHandler):
    """Exports teacher registration table as CSV.

    """
    @require_permission(BaseHandler.AUTHENTICATED)
    def get(self):
        registrations = self.sql_session.query(TeacherRegistration)\
            .options(joinedload('district'))\
            .options(joinedload('school'))\
            .all()

        self.set_header("Content-Type", "text/csv")
        self.set_header("Content-Disposition",
                        "attachment; filename=\"registrations.csv\"")

        writer = csv.writer(self)
        writer.writerow([
            'Timestamp',
            'First name',
            'Last name',
            'Email',
            'District',
            'School',
            'Password',
        ])
        writer.writerows([
            [
                reg.timestamp.isoformat(b' '),
                reg.first_name.encode('utf8'),
                reg.last_name.encode('utf8'),
                reg.email.encode('utf8'),
                reg.district.name.encode('utf8') if reg.district else '',
                reg.school.name.encode('utf8') if reg.school else '',
                reg.school.password.encode('ascii') if reg.school else '',
            ]
            for reg in registrations
        ])
        self.finish()
