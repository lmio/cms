#!/usr/bin/env python3

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2024 Vytis Banaitis <vytis.banaitis@gmail.com>
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

"""Python programming language, version 3.11, definition."""

from .python3_cpython import Python3CPython


__all__ = ["Python311CPython"]



class Python311CPython(Python3CPython):
    """This defines the Python programming language, version 3.11
    using the default interpreter in the system.

    """

    PYTHON_BIN = "/usr/bin/python3.11"

    @property
    def name(self):
        """See Language.name."""
        return "Python 3.11 / CPython"
