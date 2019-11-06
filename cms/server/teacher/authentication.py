#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2019 Vytis Banaitis <vytis.banaitis@gmail.com>
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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future.builtins.disabled import *  # noqa
from future.builtins import *  # noqa

import json
import logging
from datetime import timedelta

from cms import config
from cms.db import District, School
from cmscommon.datetime import make_datetime, make_timestamp


__all__ = ['validate_login', 'authenticate_request']


logger = logging.getLogger(__name__)


def get_user_from_db(object_id, session):
    """Return the user object dependent on current configuration.

    object_id (int): user object database ID.
    session (Session): SQLAlchemy session.

    return (District|School|None):  the user object.

    """
    if config.teacher_login_kind == "district":
        return District.get_from_id(object_id, session)
    elif config.teacher_login_kind == "school":
        return School.get_from_id(object_id, session)
    else:
        return None


def validate_login(sql_session, timestamp, login_id, password, ip_address):
    """Authenticate a teacher logging in, with user id and password.

    sql_session (Session): SQLAlchemy session.
    timestamp (datetime): the date and the time of the request.
    login_id (str): the database id of the district or school.
    password (str): the password the user provided.
    ip_address (IPv4Address|IPv6Address): the IP address the request
        came from.

    return ((District|School, bytes)|(None, None)): if the user
        couldn't be authenticated then return a pair of None, otherwise
        return the district or school that they wanted to authenticate
        as and a refreshed cookie.
    """
    try:
        login_id = int(login_id)
    except ValueError:
        logger.info("Unsuccessful teacher login attempt from IP address %s, "
                    "as user id %r, at %s", ip_address, login_id, timestamp)
        return None, None

    obj = get_user_from_db(login_id, sql_session)

    if obj is None or obj.password != password:
        logger.info("Unsuccessful teacher login attempt from IP address %s, "
                    "as user id %r, at %s", ip_address, login_id, timestamp)
        return None, None

    logger.info("Successful teacher login attempt from IP address %s, as user "
                "id %r, at %s", ip_address, login_id, timestamp)
    return (obj,
            json.dumps([config.teacher_login_kind,
                        obj.id,
                        obj.password,
                        make_timestamp(timestamp)]))


def authenticate_request(sql_session, timestamp, cookie):
    """Authenticate a user returning to the site, with a cookie.

    sql_session (Session): SQLAlchemy session.
    timestamp (datetime): the date and the time of the request.
    cookie (bytes): the cookie the user's browser provided in the
        request.

    return ((District|School, bytes)|(None, None)): if the user
        couldn't be authenticated then return a pair of None, otherwise
        return the district or school that they wanted to authenticate
        as and a refreshed cookie.
    """
    # Parse cookie.
    try:
        cookie = json.loads(cookie)
        kind = cookie[0]
        object_id = cookie[1]
        password = cookie[2]
        last_update = make_datetime(cookie[3])
        assert kind == config.teacher_login_kind
    except Exception as e:
        # Cookies are stored securely and thus cannot be tampered with:
        # this is either a programming or a configuration error.
        logger.warning("Invalid cookie (%s): %s", e, cookie)
        return None, None

    # Check if the cookie is expired.
    if timestamp - last_update > timedelta(seconds=config.cookie_duration):
        return None, None

    # Load the district or school from DB.
    obj = get_user_from_db(object_id, sql_session)

    # Check if district exists and password is correct.
    if obj is None or obj.password != password:
        return None, None

    return (obj,
            json.dumps([config.teacher_login_kind,
                        obj.id,
                        obj.password,
                        make_timestamp(timestamp)]))
