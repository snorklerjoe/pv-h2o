import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from app.dynconfig import DynConfig
from loguru import logger

class NotificationService:
    """Email notification service using SMTP configuration."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.smtp_host: Optional[str] = None
            self.smtp_port: Optional[int] = None
            self.smtp_user: Optional[str] = None
            self.smtp_password: Optional[str] = None
            self.from_email: Optional[str] = None
            NotificationService._initialized = True
    
    def init(self) -> None:
        """Initialize notification service with dynconfig SMTP settings."""
        self.smtp_host = DynConfig.notify_smtp_server
        self.smtp_port = DynConfig.notify_smtp_port
        self.smtp_user = DynConfig.notify_smtp_user
        self.smtp_password = DynConfig.notify_smtp_pass
        self.from_email = DynConfig.notify_smtp_user
    
    def send_email(self, to: str, subject: str, body: str, 
                   is_html: bool = False) -> bool:
        """Send an email notification."""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html' if is_html else 'plain'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False
    
    def send_batch(self, recipients: list[str], subject: str, body: str,
                   is_html: bool = False) -> int:
        """Send email to multiple recipients. Returns count of successful sends."""
        success_count = 0
        for recipient in recipients:
            if self.send_email(recipient, subject, body, is_html):
                success_count += 1
        return success_count

    def notify(self, subject, body) -> None:
        """ Sends a notification as per config """
        if DynConfig.notify_email_enabled:
            self.init()  # Update SMTP settings from latest config
            recipients: list[str] = DynConfig.notify_email_recipient.split(',')
            self.send_batch(recipients, subject, body, False)
        else:
            logger.error("Attempt to send email when email notifications are turned off.")
            logger.debug(f"Failed notification attempt: {subject} : {body}")
