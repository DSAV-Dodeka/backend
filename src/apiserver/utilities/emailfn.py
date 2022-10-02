import logging
from typing import Optional, Any

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

from jinja2 import Environment

from apiserver.define import (
    template_env,
    onboard_email,
    smtp_server,
    smtp_port,
    loc_dict,
    LOGGER_NAME,
)

__all__ = ["send_email", "send_email_vars"]

logger = logging.getLogger(LOGGER_NAME)


def send_email(
    template: str,
    receiver_email: str,
    mail_pass: str,
    subject: str,
    add_vars: Optional[dict[str, Any]] = None,
) -> None:
    """Automatically loads the localization dictionary from the filesystem, with add_vars replacing any keys and adding
    any ones that are undefined by the localization."""
    if add_vars is None:
        add_vars = dict()
    templ_vars = loc_dict | add_vars
    send_email_vars(
        template,
        template_env,
        templ_vars,
        receiver_email,
        mail_pass,
        onboard_email,
        smtp_server,
        smtp_port,
        subject,
    )


def send_email_vars(
    template_name: str,
    loaded_env: Environment,
    templ_vars: dict[str, Any],
    receiver_email: str,
    mail_pass: str,
    from_email: str,
    l_smtp_server: str,
    l_smtp_port: int,
    subject: str,
) -> None:
    template = loaded_env.get_template(template_name)

    html = template.render(templ_vars)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = receiver_email
    msg["Date"] = formatdate(localtime=True)

    html_msg = MIMEText(html, "html")

    msg.attach(html_msg)

    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL(l_smtp_server, l_smtp_port, context=context) as server:
            server.login(from_email, mail_pass)
            server.sendmail(from_email, receiver_email, msg.as_string())
            logger.debug(
                f"Sent an email from {from_email} to {receiver_email} with subject"
                f" '{subject}'"
            )
    except smtplib.SMTPException as e:
        logger.debug(str(e))
