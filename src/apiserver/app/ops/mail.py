from typing import Optional, Any

from apiserver.app.define import (
    template_env,
    onboard_email,
    smtp_server,
    smtp_port,
    loc_dict,
)

__all__ = ["send_email", "send_email_vars"]

from apiserver.lib.actions.mail import send_email_vars


def send_email(
    logger,
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
        logger,
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
