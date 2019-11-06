#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2014-2016 Vytis Banaitis <vytis.banaitis@gmail.com>
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

"""Teacher web server database interface for SQLAlchemy.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future.builtins.disabled import *  # noqa
from future.builtins import *  # noqa

from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import DateTime, Integer, Unicode
from sqlalchemy.orm import relationship

from . import Base


class District(Base):
    """Class to store a school district.

    """

    __tablename__ = 'districts'

    # Auto increment primary key.
    id = Column(
        Integer,
        primary_key=True)

    # Name of the district
    name = Column(
        Unicode,
        nullable=False)

    # TWS login password.
    password = Column(
        Unicode,
        nullable=False)

    # These one-to-many relationships are the reversed directions of
    # the ones defined in the "child" classes using foreign keys.

    schools = relationship(
        "School",
        cascade="all, delete-orphan",
        passive_deletes=True,
        back_populates="district")

    users = relationship(
        "User",
        cascade="all",
        passive_deletes=True,
        back_populates="district")


class School(Base):
    """Class to store a school.

    """

    __tablename__ = 'schools'

    # Auto increment primary key.
    id = Column(
        Integer,
        primary_key=True)

    # Name of the school
    name = Column(
        Unicode,
        nullable=False)

    # TWS login password.
    password = Column(
        Unicode,
        nullable=False)

    # District (id and object) this school belongs to.
    district_id = Column(
        Integer,
        ForeignKey(District.id,
                   onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True)
    district = relationship(
        District,
        back_populates="schools")

    # These one-to-many relationships are the reversed directions of
    # the ones defined in the "child" classes using foreign keys.

    users = relationship(
        "User",
        cascade="all",
        passive_deletes=True,
        back_populates="school")


class TeacherRegistration(Base):
    """Class to store teacher registration details.

    """

    __tablename__ = 'teacher_registrations'

    # Auto increment primary key.
    id = Column(
        Integer,
        primary_key=True)

    # Real name of the teacher.
    first_name = Column(
        Unicode,
        nullable=False)
    last_name = Column(
        Unicode,
        nullable=False)

    # Email for any communications.
    email = Column(
        Unicode,
        nullable=False)

    # District (id and object) this teacher registered to.
    district_id = Column(
        Integer,
        ForeignKey(District.id,
                   onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
        index=True)
    district = relationship(
        District)

    # School (id and object) this teacher registered to.
    school_id = Column(
        Integer,
        ForeignKey(School.id,
                   onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
        index=True)
    school = relationship(
        School)

    # Time of the registration
    timestamp = Column(
        DateTime,
        nullable=False)
