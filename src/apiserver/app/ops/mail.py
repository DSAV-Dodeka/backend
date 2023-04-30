from typing import Optional, Any

import logging

from fastapi import BackgroundTasks
from apiserver.lib.actions.mail import send_email_vars
from apiserver.app.define import (
    template_env,
    onboard_email,
    smtp_server,
    smtp_port,
    loc_dict,
    LOGGER_NAME,
)


logger = logging.getLogger(LOGGER_NAME)

__all__ = [
    "send_signup_email",
    "send_register_email",
    "send_change_email_email",
    "send_reset_email",
]


def send_email(
    logger_sent,
    template: str,
    receiver_email: str,
    mail_pass: str,
    subject: str,
    receiver_name: Optional[str] = None,
    add_vars: Optional[dict[str, Any]] = None,
) -> None:
    """Automatically loads the localization dictionary from the filesystem, with add_vars replacing any keys and adding
    any ones that are undefined by the localization."""
    if add_vars is None:
        add_vars = dict()
    templ_vars = loc_dict | add_vars
    send_email_vars(
        logger_sent,
        template_name=template,
        has_html=True,
        loaded_env=template_env,
        templ_vars=templ_vars,
        receiver_email=receiver_email,
        receiver_name=receiver_name,
        mail_pass=mail_pass,
        from_email=onboard_email,
        from_name=loc_dict["loc"]["org_name"],
        l_smtp_server=smtp_server,
        l_smtp_port=smtp_port,
        subject=subject,
    )


def send_signup_email(
    background_tasks: BackgroundTasks,
    receiver: str,
    receiver_name: str,
    mail_pass: str,
    redirect_link: str,
    signup_link: str,
):
    add_vars = {"redirect_link": redirect_link, "signup_link": signup_link}

    def send_lam():
        send_email(
            logger,
            "confirm.jinja2",
            receiver,
            mail_pass,
            "Please confirm your email",
            receiver_name,
            add_vars=add_vars,
        )

    background_tasks.add_task(send_lam)


def send_register_email(
    background_tasks: BackgroundTasks, receiver: str, mail_pass: str, register_link: str
):
    add_vars = {"register_link": register_link}

    def send_lam():
        org_name = loc_dict["loc"]["org_name"]
        send_email(
            logger,
            "register.jinja2",
            receiver,
            mail_pass,
            f"Welcome to {org_name}",
            add_vars=add_vars,
        )

    background_tasks.add_task(send_lam)


def send_reset_email(
    background_tasks: BackgroundTasks, receiver: str, mail_pass: str, reset_link: str
):
    add_vars = {
        "reset_link": reset_link,
    }

    def send_lam():
        send_email(
            logger,
            "passwordchange.jinja2",
            receiver,
            mail_pass,
            "Request for password reset",
            add_vars=add_vars,
        )

    background_tasks.add_task(send_lam)


def send_change_email_email(
    background_tasks: BackgroundTasks,
    receiver: str,
    mail_pass: str,
    reset_link: str,
    old_email: str,
):
    add_vars = {
        "old_email": old_email,
        "reset_link": reset_link,
    }

    def send_lam():
        send_email(
            logger,
            "emailchange.jinja2",
            receiver,
            mail_pass,
            "Please confirm your new email",
            add_vars=add_vars,
        )

    background_tasks.add_task(send_lam)
