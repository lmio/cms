#!/usr/bin/env python2
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
from __future__ import print_function
from __future__ import unicode_literals

import json

from cms.grading.ScoreType import ScoreTypeGroup


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

    def compute_score(self, submission_result):
        """See ScoreType.compute_score."""
        # Actually, this means it didn't even compile!
        if not submission_result.evaluated():
            return 0.0, "[]", 0.0, "[]", ["%lg" % 0.0 for _ in self.parameters]

        score = 0
        subtasks = []
        public_score = 0
        public_subtasks = []
        ranking_details = []

        targets = self.retrieve_target_testcases()
        evaluations = {ev.codename: ev for ev in submission_result.evaluations}
        tc_indices = {codename: idx
                      for idx, codename in enumerate(sorted(evaluations.keys()), 1)}
        score_precision = submission_result.submission.task.score_precision

        for st_idx, parameter in enumerate(self.parameters):
            target = targets[st_idx]

            testcases = []
            public_testcases = []
            for tc_idx in target:
                tc_outcome = self.get_public_outcome(
                    float(evaluations[tc_idx].outcome), parameter)

                testcases.append({
                    "idx": tc_indices[tc_idx],
                    "outcome": tc_outcome,
                    "text": evaluations[tc_idx].text,
                    "time": evaluations[tc_idx].execution_time,
                    "memory": evaluations[tc_idx].execution_memory})
                if self.public_testcases[tc_idx]:
                    public_testcases.append(testcases[-1])
                else:
                    public_testcases.append({"idx": tc_indices[tc_idx]})

            st_score_fraction = self.reduce(
                [float(evaluations[tc_idx].outcome) for tc_idx in target],
                parameter)
            st_score = st_score_fraction * parameter[0]

            score += st_score
            subtasks.append({
                "idx": st_idx + 1,
                # We store the fraction so that an "example" testcase
                # with a max score of zero is still properly rendered as
                # correct or incorrect.
                "score_fraction": st_score_fraction,
                "score": round(st_score, score_precision),
                "max_score": round(parameter[0], score_precision),
                "testcases": testcases})
            if all(self.public_testcases[tc_idx] for tc_idx in target):
                public_score += st_score
                public_subtasks.append(subtasks[-1])
            else:
                public_subtasks.append({"idx": st_idx + 1,
                                        "testcases": public_testcases})
            ranking_details.append("%g" % round(st_score, score_precision))

        score = round(score, score_precision)
        public_score = round(public_score, score_precision)

        return score, json.dumps(subtasks), \
            public_score, json.dumps(public_subtasks), \
            ranking_details

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
