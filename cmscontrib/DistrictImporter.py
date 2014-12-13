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

"""This utility imports a list of districts from a YAML file.

"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

# We enable monkey patching to make many libraries gevent-friendly
# (for instance, urllib3, used by requests)
import gevent.monkey
gevent.monkey.patch_all()


import argparse
import io
import sys
import yaml

from cms import utf8_decoder
from cms.db import SessionGen, District


def import_districts(filename, clean):
    with io.open(filename) as f:
        districts = yaml.load(f)

    with SessionGen() as session:
        old_districts = {d.name: d for d in session.query(District).all()}
        for d in districts:
            old_district = old_districts.get(d["name"])
            if old_district is None:
                # Create a new district
                district = District(**d)
                session.add(district)
            else:
                # Update the district
                old_district.set_attrs(d)
                del old_districts[d["name"]]
        if clean:
            # Remove districts not in the new list
            for district in old_districts.itervalues():
                session.delete(district)
        session.commit()


def main():
    """Parse arguments and launch process.

    """
    parser = argparse.ArgumentParser(
        description="Import a list of districts.")
    parser.add_argument("-c", "--clean", action="store_true",
                        help="remove existing districts that are not in the "
                        "imported list")
    parser.add_argument("district_file", action="store", type=utf8_decoder,
                        help="file to import")
    args = parser.parse_args()

    import_districts(args.district_file, args.clean)

    return 0


if __name__ == "__main__":
    sys.exit(main())
