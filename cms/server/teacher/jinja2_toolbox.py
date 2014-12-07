#!/usr/bin/env python3

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

"""Provide a Jinja2 environment tailored to TWS.

"""

from jinja2 import PackageLoader

from cms.server.jinja2_toolbox import GLOBAL_ENVIRONMENT


TWS_ENVIRONMENT = GLOBAL_ENVIRONMENT.overlay(
    # Load templates from TWS's package (use package rather than file
    # system as that works even in case of a compressed distribution).
    loader=PackageLoader('cms.server.teacher', 'templates'))
