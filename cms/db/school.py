#!/usr/bin/env python2
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
from __future__ import print_function
from __future__ import unicode_literals

from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import Integer, Unicode
from sqlalchemy.orm import relationship, backref

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

    # Follows the description of the fields automatically added by
    # SQLAlchemy.
    # schools (list of School objects)
    # users (list of User objects)


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
        backref=backref("schools",
                        passive_deletes=True))
