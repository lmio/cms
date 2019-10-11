#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Programming contest management system
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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future.builtins.disabled import *  # noqa
from future.builtins import *  # noqa

from . import ScoreTypeGroup


# Dummy function to mark translatable string.
def N_(message):
    return message


class SharedGroupThreshold(ScoreTypeGroup):
    """A score type that allows tests to be shared between groups.
    The score for a subtask is multiplied by minimum result if the
    results of all tests in the subtask are not lower than a threshold,
    and is zero otherwise. The score type parameters
    must be in the form [[m, codes, t], [...], ...], where m is the score
    for the subtask, codes is a list of code names for tests that comprise
    this subtask, and t is the score threshold.

    """

    def retrieve_target_testcases(self):
        """See ScoreType.retrieve_target_testcases."""
        return [p[1] for p in self.parameters]

    def get_public_outcome(self, outcome, parameter):
        threshold = parameter[2]
        if outcome == 0 or outcome < threshold:
            return N_("Not correct")
        elif outcome >= 1.0:
            return N_("Correct")
        else:
            return N_("Partially correct")

    def reduce(self, outcomes, parameter):
        threshold = parameter[2]
        if all(outcome >= threshold
               for outcome in outcomes):
            return min(outcomes)
        else:
            return 0.0
