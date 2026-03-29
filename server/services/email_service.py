import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..config import settings
import logging

logger = logging.getLogger(__name__)

WELCOME_HTML = """
<html>
<body>
    <h2>Welcome to PDF Library</h2>
    <p>Hello <b>{login}</b>,</p>
    <p>Your account has been created successfully.</p>
    <p><b>Temporary Password:</b> <code>{password}</code></p>
    <p>Please log in and change your password as soon as possible.</p>
    <br>
    <p>Best regards,<br>PDF Library Team</p>
</body>
</html>
"""

RESET_HTML = """
<html>
<body>
    <h2>Password Reset Request</h2>
    <p>Hello,</p>
    <p>You requested to reset your password. Use the following code to proceed:</p>
    <p style="font-size: 24px; font-weight: bold; letter-spacing: 5px;">{code}</p>
    <p>If you did not request this, please ignore this email.</p>
    <br>
    <p>Best regards,<br>PDF Library Team</p>
</body>
</html>
"""

def send_welcome_email(email: str, username: str, temp_password: str):
    """Отправка приветственного письма с временным паролем"""
    html = WELCOME_HTML.format(login=username, password=temp_password)
    return _send_email(email, "Welcome to PDF Library", html)

def send_reset_email(email: str, code: str):
    """Отправка письма с кодом восстановления пароля"""
    html = RESET_HTML.format(code=code)
    return _send_email(email, "Password Reset Code", html)

def _send_email(to_email: str, subject: str, html_content: str):
    if not to_email:
        logger.warning(f"No recipient email. Skipping.")
        return False

    message = MIMEMultipart("alternative")
    message["From"] = settings.MAIL_FROM
    message["To"] = to_email
    message["Subject"] = subject

    message.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
        logger.info(f"Email '{subject}' sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False