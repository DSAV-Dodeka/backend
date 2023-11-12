from loguru import logger
from typing import Optional, Any

from jinja2 import Environment
import smtplib
from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import formatdate


def send_email_vars(
    template_name: str,
    has_html: bool,
    loaded_env: Environment,
    templ_vars: dict[str, Any],
    receiver_email: str,
    mail_pass: str,
    from_email: str,
    l_smtp_server: str,
    l_smtp_port: int,
    subject: str,
    receiver_name: Optional[str] = None,
    from_name: Optional[str] = None,
) -> None:
    template = loaded_env.get_template(template_name)

    txt_content = template.render(templ_vars)

    # Create the base text message.
    msg = EmailMessage()
    msg["Subject"] = subject
    from_email_name = from_name if from_name is not None else from_email
    from_user, from_domain = from_email.split("@")
    msg["From"] = Address(from_email_name, from_user, from_domain)
    receiver_email_name = receiver_name if receiver_name is not None else receiver_email
    receiver_user, receiver_domain = receiver_email.split("@")
    msg["To"] = Address(receiver_email_name, receiver_user, receiver_domain)
    msg["Date"] = formatdate(localtime=True)

    msg.set_content(txt_content)

    if has_html:
        html_name = f"{template_name.removesuffix('.jinja2')}.html.jinja2"
        template = loaded_env.get_template(html_name)

        html = template.render(templ_vars)

        # Necessary for images later
        # cid = make_msgid(domain=from_domain)
        # html.format(some_cid=cid[1:-1])
        # note that we needed to peel the <> off the msgid for use in the html.
        # Also, again only for if we need images

        msg.add_alternative(html, subtype="html")

    logger.debug(f"{l_smtp_server} {l_smtp_port}")

    try:
        with smtplib.SMTP(l_smtp_server, l_smtp_port) as server:
            server.starttls()
            server.login(from_email, mail_pass)
            server.sendmail(from_email, receiver_email, msg.as_string())
            logger.debug(
                f"Sent an email from {from_email} to {receiver_email} with subject"
                f" '{subject}'"
            )
    except smtplib.SMTPException as e:
        logger.debug(str(e))
