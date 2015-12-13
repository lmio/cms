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

    def max_scores(self):
        """Compute the maximum score of a submission.

        returns (float, float): maximum score overall and public.

        """
        score = 0.0
        public_score = 0.0
        headers = list()

        for i, parameter in enumerate(self.parameters):
            score += parameter[0]
            if all(self.public_testcases[idx]
                   for idx in parameter[1]):
                public_score += parameter[0]
            headers += ["Subtask %d (%g)" % (i + 1, parameter[0])]

        return score, public_score, headers

    def compute_score(self, submission_result):
        """Compute the score of a submission.

        submission_id (int): the submission to evaluate.
        returns (float): the score

        """
        # Actually, this means it didn't even compile!
        if not submission_result.evaluated():
            return 0.0, "[]", 0.0, "[]", \
                json.dumps(["%lg" % 0.0 for _ in self.parameters])

        evaluations = dict((ev.codename, ev)
                           for ev in submission_result.evaluations)
        subtasks = []
        public_subtasks = []
        ranking_details = []

        for st_idx, parameter in enumerate(self.parameters):
            st_result = self.reduce([float(evaluations[idx].outcome)
                                     for idx in parameter[1]],
                                    parameter)
            st_outcome = self.get_subtask_outcome(st_result)
            st_score = st_result * parameter[0]
            st_public = all(self.public_testcases[idx]
                            for idx in parameter[1])
            tc_outcomes = dict((
                idx,
                self.get_public_outcome(
                    float(evaluations[idx].outcome), parameter)
                ) for idx in parameter[1])

            testcases = []
            public_testcases = []
            for idx in parameter[1]:
                testcases.append({
                    "idx": idx,
                    "outcome": tc_outcomes[idx],
                    "text": evaluations[idx].text,
                    "time": evaluations[idx].execution_time,
                    "memory": evaluations[idx].execution_memory,
                    })
                if self.public_testcases[idx]:
                    public_testcases.append(testcases[-1])
                else:
                    public_testcases.append({"idx": idx})
            subtasks.append({
                "idx": st_idx + 1,
                "outcome": st_outcome,
                "score": st_score,
                "max_score": parameter[0],
                "testcases": testcases,
                })
            if st_public:
                public_subtasks.append(subtasks[-1])
            else:
                public_subtasks.append({
                    "idx": st_idx + 1,
                    "testcases": public_testcases,
                    })

            ranking_details.append("%g" % round(st_score, 2))

        score = sum(st["score"] for st in subtasks)
        public_score = sum(st["score"]
                           for st in public_subtasks
                           if "score" in st)

        return score, json.dumps(subtasks), \
            public_score, json.dumps(public_subtasks), \
            json.dumps(ranking_details)

    def get_public_outcome(self, outcome, parameter):
        threshold = parameter[2]
        if outcome == 0 or outcome < threshold:
            return N_("Not correct")
        elif outcome >= 1.0:
            return N_("Correct")
        else:
            return N_("Partially correct")

    def get_subtask_outcome(self, outcome):
        if outcome == 0:
            return "notcorrect"
        elif outcome >= 1.0:
            return "correct"
        else:
            return "partiallycorrect"

    def reduce(self, outcomes, parameter):
        threshold = parameter[2]
        if all(outcome >= threshold
               for outcome in outcomes):
            return min(outcomes)
        else:
            return 0.0
