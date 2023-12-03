from typing import Optional, Any, TypedDict


from fastapi import BackgroundTasks
from loguru import logger

from apiserver.env import Config
from apiserver.lib.actions.mail import send_email_vars
from apiserver.define import template_env, loc_dict, DEFINE


__all__ = [
    "send_signup_email",
    "send_register_email",
    "send_change_email_email",
    "send_reset_email",
    "mail_from_config",
]


class MailServer(TypedDict):
    mail_pass: str
    smtp_server: str
    smtp_port: int


def mail_from_config(config: Config) -> Optional[MailServer]:
    if not config.MAIL_ENABLED:
        logger.debug("Mail disabled, not sending email.")
        return None
    return {
        "mail_pass": config.MAIL_PASS,
        "smtp_port": config.SMTP_PORT,
        "smtp_server": config.SMTP_SERVER,
    }


def send_email(
    template: str,
    receiver_email: str,
    mail_server: Optional[MailServer],
    subject: str,
    receiver_name: Optional[str] = None,
    add_vars: Optional[dict[str, Any]] = None,
) -> None:
    """Automatically loads the localization dictionary from the filesystem, with add_vars replacing any keys and adding
    any ones that are undefined by the localization."""
    if mail_server is None:
        # Don't send anything
        return
    if add_vars is None:
        add_vars = dict()
    templ_vars = loc_dict | add_vars
    send_email_vars(
        template_name=template,
        has_html=True,
        loaded_env=template_env,
        templ_vars=templ_vars,
        receiver_email=receiver_email,
        receiver_name=receiver_name,
        mail_pass=mail_server["mail_pass"],
        from_email=DEFINE.onboard_email,
        from_name=loc_dict["loc"]["org_name"],
        l_smtp_server=mail_server["smtp_server"],
        l_smtp_port=mail_server["smtp_port"],
        subject=subject,
    )


def send_signup_email(
    background_tasks: BackgroundTasks,
    receiver: str,
    receiver_name: str,
    mail_server: Optional[MailServer],
    redirect_link: str,
    signup_link: str,
) -> None:
    add_vars = {"redirect_link": redirect_link, "signup_link": signup_link}

    def send_lam() -> None:
        send_email(
            "confirm.jinja2",
            receiver,
            mail_server,
            "Please confirm your email",
            receiver_name,
            add_vars=add_vars,
        )

    background_tasks.add_task(send_lam)


def send_register_email(
    background_tasks: BackgroundTasks,
    receiver: str,
    mail_server: Optional[MailServer],
    register_link: str,
) -> None:
    add_vars = {"register_link": register_link}

    def send_lam() -> None:
        org_name = loc_dict["loc"]["org_name"]
        send_email(
            "register.jinja2",
            receiver,
            mail_server,
            f"Welcome to {org_name}",
            add_vars=add_vars,
        )

    background_tasks.add_task(send_lam)


def send_reset_email(
    background_tasks: BackgroundTasks,
    receiver: str,
    mail_server: Optional[MailServer],
    reset_link: str,
) -> None:
    add_vars = {
        "reset_link": reset_link,
    }

    def send_lam() -> None:
        send_email(
            "passwordchange.jinja2",
            receiver,
            mail_server,
            "Request for password reset",
            add_vars=add_vars,
        )

    background_tasks.add_task(send_lam)


def send_change_email_email(
    background_tasks: BackgroundTasks,
    receiver: str,
    mail_server: Optional[MailServer],
    reset_link: str,
    old_email: str,
) -> None:
    add_vars = {
        "old_email": old_email,
        "reset_link": reset_link,
    }

    def send_lam() -> None:
        send_email(
            "emailchange.jinja2",
            receiver,
            mail_server,
            "Please confirm your new email",
            add_vars=add_vars,
        )

    background_tasks.add_task(send_lam)
