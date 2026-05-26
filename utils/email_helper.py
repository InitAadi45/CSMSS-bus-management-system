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
    # ---------------------------------------------------------
    # EMAIL CONFIGURATION TEMPLATE
    # TODO: Fill in your Gmail address and App Password below.
    # To get an App Password: Go to Google Account -> Security -> App Passwords
    # ---------------------------------------------------------
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = os.environ.get('SMTP_PORT', 587)
    
    smtp_user = os.environ.get('SMTP_USER', 'blackboneishere@gmail.com')  # Your Gmail address
    smtp_pass = os.environ.get('SMTP_PASS', 'ncct ghez ssbw ofuw')         # Your 16-char App Password
    
    sender_email = os.environ.get('SMTP_SENDER', smtp_user)
    # ---------------------------------------------------------

    msg_info = f"""
========================================
[SIMULATED EMAIL SENT]
To: {to_email}
Subject: {subject}
Message:
{body_content}
========================================
"""

    if not smtp_user or not smtp_pass or not smtp_server:
        # Fallback: print to console if config missing
        print(msg_info, file=sys.stderr)
        return True

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject

        formal_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; padding: 20px; border-radius: 8px; background-color: #ffffff;">
                <h2 style="color: #1e3a8a; border-bottom: 2px solid #1e3a8a; padding-bottom: 10px; margin-top: 0;">CSMSS Transport Department</h2>
                <div style="padding: 20px 0;">
                    {body_content}
                </div>
                <div style="margin-top: 30px; border-top: 1px solid #e0e0e0; padding-top: 20px; font-size: 0.9em; color: #666;">
                    <p style="margin-bottom: 5px;">Sincerely,</p>
                    <p style="margin: 0;"><strong>Transport Cell</strong><br>CSMSS Chhatrapati Shahu College of Engineering</p>
                    <p style="margin-top: 15px; font-size: 0.85em;"><em>Note: This is an automated formal notification. Please do not reply directly to this email.</em></p>
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(formal_body, 'html'))

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
