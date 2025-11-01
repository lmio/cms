#!/usr/bin/env python3

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2025 Vytis Banaitis <vytis.banaitis@gmail.com>
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

from . import ScoreTypeGroup
from .GroupMin import GroupMin


class ScoreTypeSimpleGroup(ScoreTypeGroup):
    """Intermediate class with a simpler result template.

    Instead of grouping test cases into separate sections for each
    group/subtask, all testcases are listed in a single table.

    """

    TEMPLATE = """\
<table class="testcase-list">
    <thead>
        <tr>
            <th class="idx">
                {% trans %}#{% endtrans %}
            </th>
            <th class="outcome">
                {% trans %}Outcome{% endtrans %}
            </th>
            <th class="details">
                {% trans %}Details{% endtrans %}
            </th>
{% if feedback_level == FEEDBACK_LEVEL_FULL %}
            <th class="execution-time">
                {% trans %}Execution time{% endtrans %}
            </th>
            <th class="memory-used">
                {% trans %}Memory used{% endtrans %}
            </th>
{% endif %}
            <th class="score">
                {% trans %}Score{% endtrans %}
            </th>
        </tr>
    </thead>
    <tbody>
{% for st in details %}
    {% for tc in st["testcases"] %}
        {% if "outcome" in tc
               and (feedback_level == FEEDBACK_LEVEL_FULL
                    or tc["show_in_restricted_feedback"]) %}
            {% if tc["outcome"] == "Correct" %}
                <tr class="correct">
            {% elif tc["outcome"] == "Not correct" %}
                <tr class="notcorrect">
            {% else %}
                <tr class="partiallycorrect">
            {% endif %}
                    <td class="idx">{{ tc["idx"] if feedback_level == FEEDBACK_LEVEL_FULL else loop.index }}</td>
                    <td class="outcome">{{ _(tc["outcome"]) }}</td>
                    <td class="details">
                      {{ tc["text"]|format_status_text }}
                    </td>
            {% if feedback_level == FEEDBACK_LEVEL_FULL %}
                    <td class="execution-time">
                {% if "time" in tc and tc["time"] is not none %}
                        {{ tc["time"]|format_duration }}
                {% else %}
                        {% trans %}N/A{% endtrans %}
                {% endif %}
                    </td>
                    <td class="memory-used">
                {% if "memory" in tc and tc["memory"] is not none %}
                        {{ tc["memory"]|format_size }}
                {% else %}
                        {% trans %}N/A{% endtrans %}
                {% endif %}
                    </td>
            {% endif %}
        {% else %}
                <tr class="undefined">
                    <td class="idx">{{ tc["idx"] if feedback_level == FEEDBACK_LEVEL_FULL else loop.index }}</td>
            {% if feedback_level == FEEDBACK_LEVEL_FULL %}
                    <td colspan="4">
            {% else %}
                    <td colspan="2">
            {% endif %}
                        {% trans %}N/A{% endtrans %}
                    </td>
        {% endif %}
        {% if loop.first %}
                    <td class="score" rowspan="{{ loop.length }}">
            {% if "score_fraction" in st %}
                {% if st["score_fraction"] >= 1.0 %}
                        <div class="score correct">
                {% elif st["score_fraction"] <= 0.0 %}
                        <div class="score notcorrect">
                {% else %}
                        <div class="score partiallycorrect">
                {% endif %}
            {% else %}
                        <div class="score undefined">
            {% endif %}
            {% if "score" in st and "max_score" in st %}
                            {{ st["score"]|format_decimal }}
                             / {{ st["max_score"]|format_decimal }}
            {% else %}
                            {% trans %}N/A{% endtrans %}
            {% endif %}
                        </div>
                    </td>
        {% endif %}
                </tr>
    {% endfor %}
{% endfor %}
    </tbody>
</table>
"""


class SimpleGroupMin(ScoreTypeSimpleGroup, GroupMin):
    pass
