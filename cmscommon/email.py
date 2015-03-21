#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2015 Vytis Banaitis <vytis.banaitis@gmail.com>
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


import logging
import smtplib
import socket
from email.mime.text import MIMEText

from cms import config


logger = logging.getLogger(__name__)


def send_email(to, subject, message):
    """Send an email.
    
    to (string): recipient address
    subject (string): email subject
    message (string): email body
    
    return (bool): whether the email was sent succesfully
    """
    if not config.email_host:
        return False

    msg = MIMEText(message.encode('utf-8'))
    msg.set_charset('utf-8')
    msg['From'] = config.email_from_address
    msg['To'] = to
    msg['Subject'] = subject

    try:
        smtp = smtplib.SMTP(config.email_host, config.email_port)
    except (smtplib.SMTPConnectError, socket.timeout):
        logger.error("Unable to connect to SMTP server.", exc_info=True)
        return False

    try:
        if config.email_tls:
            smtp.starttls()
        if config.email_username is not None:
            smtp.login(config.email_username, config.email_password)
        smtp.sendmail(config.email_from_address, [to], msg.as_string())
    except smtplib.SMTPException:
        logger.error("SMTP error", exc_info=True)
        return False
    finally:
        try:
            smtp.quit()
        except smtplib.SMTPServerDisconnected:
            smtp.close()
    
    return True
