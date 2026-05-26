import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import sys

def send_bus_email(to_email, subject, body_content):
    """
    Sends SMTP email to student or staff.
    Falls back to console logger if SMTP configuration is missing or fails.
    """
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = os.environ.get('SMTP_PORT', 587)
    smtp_user = os.environ.get('SMTP_USER','blackboneishere@gmail.com')
    smtp_pass = os.environ.get('SMTP_PASS','ncct ghez ssbw ofuw')
    sender_email = os.environ.get('SMTP_SENDER', 'no-reply@csmss.engg.edu.in')

    msg_info = f"""
========================================
[SIMULATED EMAIL SENT]
To: {to_email}
Subject: {subject}
Message:
{body_content}
========================================
"""

    if not smtp_server or not smtp_user or not smtp_pass:
        print(msg_info, file=sys.stderr)
        return True

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body_content, 'html'))

        # Standard TLS connection
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        print(f"[SMTP EMAIL SUCCESS] Sent to {to_email}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[SMTP EMAIL ERROR] Failed to send email to {to_email}. Error: {e}", file=sys.stderr)
        print(msg_info, file=sys.stderr)
        return False
