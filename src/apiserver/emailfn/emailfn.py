from typing import Optional

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

from jinja2 import Environment

from apiserver.define import template_env, onboard_email, smtp_server, smtp_port, loc_dict

__all__ = ['send_email', 'send_email_vars']


def send_email(template: str, receiver_email: str, mail_pass: str, add_vars: Optional[dict] = None):
    """ Automatically loads the localization dictionary from the filesystem, with add_vars replacing any keys and adding
    any ones that are undefined by the localization. """
    if add_vars is None:
        add_vars = dict()
    templ_vars = {
        **loc_dict,
        **add_vars
    }
    send_email_vars(template, template_env, templ_vars, receiver_email, mail_pass, onboard_email, smtp_server,
                    smtp_port)


def send_email_vars(template: str, loaded_env: Environment, templ_vars: dict, receiver_email: str, mail_pass: str,
                    from_email, l_smtp_server, l_smtp_port):
    template = loaded_env.get_template(template)

    html = template.render(templ_vars)

    msg = MIMEMultipart("alternative")
    msg['Subject'] = 'Multipart'
    msg['From'] = from_email
    msg['To'] = receiver_email
    msg["Date"] = formatdate(localtime=True)

    html_msg = MIMEText(html, "html")

    msg.attach(html_msg)

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(l_smtp_server, l_smtp_port, context=context) as server:
        server.login(from_email, mail_pass)
        server.sendmail(from_email, receiver_email, msg.as_string())
