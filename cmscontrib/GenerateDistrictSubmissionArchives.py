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

"""This utility collects submissions from participants of each district,
and archives them into downloadable zip files.

"""

# We enable monkey patching to make many libraries gevent-friendly
# (for instance, urllib3, used by requests)
import gevent.monkey
gevent.monkey.patch_all()  # noqa

import argparse
import io
import logging
import sys
import zipfile
from shutil import copyfileobj

import babel.dates
from sqlalchemy.orm import joinedload, contains_eager

from cms import config
from cms.db import Contest, SessionGen, District, DistrictSubmissionArchive, Submission, Participation, User, FSObject, \
    Task, SubmissionResult
from cms.db.filecacher import FileCacher
from cms.grading.languagemanager import get_language


logger = logging.getLogger(__name__)


def localtime(value, timezone):
    tzinfo = babel.dates.get_timezone(timezone)
    value = value.replace(tzinfo=babel.dates.UTC).astimezone(tzinfo)
    if hasattr(tzinfo, 'normalize'):  # pytz
        value = tzinfo.normalize(value)
    return value


def collect_submissions(contest_id, replace, timezone):
    with SessionGen() as session:
        contest = Contest.get_from_id(contest_id, session)

        for district in session.query(District).all():
            collect_archive(contest, district, session, replace, timezone)
        session.commit()


def collect_archive(contest, district, session, replace, timezone):
    archive = session.query(DistrictSubmissionArchive).filter(
        DistrictSubmissionArchive.contest_id == contest.id,
        DistrictSubmissionArchive.district_id == district.id,
    ).first()
    if archive and not replace:
        logger.warning("Archive for contest '%s' and district '%s' already exists. Skipping.",
                       contest.name, district.name)
        return

    logger.info("Collecting submissions for contest '%s' and district '%s'...",
                contest.name, district.name)
    submissions = (
        session.query(Submission)
        .join(Participation)
        .join(User)
        .filter(
            Participation.contest_id == contest.id,
            User.district_id == district.id,
            Submission.official == True,
            Participation.hidden == False,
        )
        .join(Task)
        .outerjoin(SubmissionResult)
        .filter(SubmissionResult.dataset_id == Task.active_dataset_id)
        .options(contains_eager(Submission.participation).contains_eager(Participation.user))
        .options(joinedload(Submission.files))
        .options(contains_eager(Submission.results))
        .all()
    )
    if not submissions:
        logger.warning("No submissions found.")
        return

    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as zf:
        for submission in submissions:
            username = submission.participation.user.username
            taskname = submission.task.name
            timestamp = localtime(submission.timestamp, timezone)
            basename = f"{timestamp:%Y%m%d-%H%M%S}"
            extension = get_language(submission.language).source_extension

            sr = submission.get_result(submission.task.active_dataset)
            if sr is None or not sr.scored():
                logger.warning("Submission %d (%s, %s, %s) is not scored",
                               submission.id, username, taskname, basename)
            elif not sr.compilation_succeeded():
                basename += '-x'
            else:
                basename = f"{basename}-{sr.score:g}"

            if len(submission.task.submission_format) > 1:
                path = f"{username}/{taskname}/{basename}"
                filename = None
            else:
                path = f"{username}/{taskname}"
                filename = f"{basename}{extension}"

            for name, file in submission.files.items():
                this_filename = filename or name.replace(".%l", extension)
                zip_info = zipfile.ZipInfo(f"{path}/{this_filename}", timestamp.timetuple()[:6])
                zip_info.compress_type = zipfile.ZIP_DEFLATED

                fso = FSObject.get_from_digest(file.digest, session)
                with fso.get_lobject(mode="rb") as source, zf.open(zip_info, "w") as target:
                    copyfileobj(source, target)
    data.seek(0)

    try:
        file_cacher = FileCacher()
        digest = file_cacher.put_file_from_fobj(
            data,
            f"Submission archive for contest '{contest.name}' and district '{district.name}'"
        )
    except Exception:
        logger.exception("Archive storage failed.")
        sys.exit(1)

    if archive is None:
        archive = DistrictSubmissionArchive(district=district, contest=contest, digest=digest)
        session.add(archive)
    else:
        archive.digest = digest


def main():
    """Parse arguments and launch process."""
    parser = argparse.ArgumentParser(description="Collect district submission archives.")
    parser.add_argument("-c", "--contest-id", action="store", type=int,
                        help="id of contest (default: all TWS enabled contests)")
    parser.add_argument("-r", "--replace", action="store_true",
                        help="replace existing archives")
    parser.add_argument("-t", "--timezone", action="store",
                        help="timezone for timestamps in file names (default: local)")
    args = parser.parse_args()

    if args.contest_id is not None:
        collect_submissions(args.contest_id, args.replace, args.timezone)
    else:
        for contest_id in config.teacher_active_contests:
            collect_submissions(contest_id, args.replace, args.timezone)

    return 0


if __name__ == "__main__":
    sys.exit(main())
