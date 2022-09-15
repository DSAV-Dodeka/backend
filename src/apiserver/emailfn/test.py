import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

import tomli
from jinja2 import Environment, FileSystemLoader, select_autoescape

from apiserver.resources import res_path, project_path

template_env = Environment(
    loader=FileSystemLoader(res_path.joinpath("templates")),
    autoescape=select_autoescape()
)


sender_email = "comcom@dsavdodeka.nl"
receiver_email = "comcom@dsavdodeka.nl"

msg = MIMEMultipart("alternative")
msg['Subject'] = 'Multipart'
msg['From'] = sender_email
msg['To'] = receiver_email
msg["Date"] = formatdate(localtime=True)

dct = {
    "hi": "Someone"
}
template = env.get_template("signup.html.jinja2")
html = template.render(dct)

html_text = MIMEText(html, "html")

msg.attach(html_text)

port = 465
with open(project_path.joinpath("localenv.toml"), "rb") as f:
    local_dict = tomli.load(f)
app_password = local_dict['email_password']

context = ssl.create_default_context()

with smtplib.SMTP_SSL("mail.dsavdodeka.nl", port, context=context) as server:
    server.login(sender_email, app_password)
    server.sendmail(sender_email, receiver_email, msg.as_string())
