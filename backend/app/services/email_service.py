"""
Email Service for sending authentication-related emails
"""
from typing import List
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr

from app.core.config import settings


# Email configuration
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME or "test@example.com",
    MAIL_PASSWORD=settings.MAIL_PASSWORD or "",
    MAIL_FROM=settings.MAIL_FROM or "test@example.com",
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

fastmail = FastMail(conf)


async def send_email(
    email_to: List[EmailStr],
    subject: str,
    html_body: str,
    text_body: str = None
):
    """Send email using FastMail"""
    message = MessageSchema(
        subject=subject,
        recipients=email_to,
        body=html_body or (text_body or ""),
        subtype="html" if html_body else "plain"
    )
    
    await fastmail.send_message(message)


def send_verification_email(email: str, name: str, user_id: int):
    """Send email verification email"""
    verification_link = f"http://localhost:4200/verify-email?user_id={user_id}"
    
    html_body = f"""
    <html>
        <body>
            <h2>Welcome to Interview Prep AI Coach!</h2>
            <p>Hi {name},</p>
            <p>Thank you for registering with Interview Prep AI Coach. Please click the link below to verify your email address:</p>
            <p><a href="{verification_link}" style="background-color: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verify Email</a></p>
            <p>If you didn't create an account, please ignore this email.</p>
            <p>Best regards,<br>Interview Prep AI Coach Team</p>
        </body>
    </html>
    """
    
    text_body = f"""
    Welcome to Interview Prep AI Coach!
    
    Hi {name},
    
    Thank you for registering with Interview Prep AI Coach. Please visit the following link to verify your email address:
    
    {verification_link}
    
    If you didn't create an account, please ignore this email.
    
    Best regards,
    Interview Prep AI Coach Team
    """
    
    # In a real application, you would use asyncio.create_task or similar
    # For now, we'll just print the email content
    print(f"Verification email for {email}:")
    print(f"Subject: Verify your email - Interview Prep AI Coach")
    print(f"Body: {text_body}")


def send_password_reset_email(email: str, name: str, reset_token: str):
    """Send password reset email"""
    reset_link = f"http://localhost:4200/reset-password?token={reset_token}"
    
    html_body = f"""
    <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>Hi {name},</p>
            <p>You requested a password reset for your Interview Prep AI Coach account. Click the link below to reset your password:</p>
            <p><a href="{reset_link}" style="background-color: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't request this reset, please ignore this email.</p>
            <p>Best regards,<br>Interview Prep AI Coach Team</p>
        </body>
    </html>
    """
    
    text_body = f"""
    Password Reset Request
    
    Hi {name},
    
    You requested a password reset for your Interview Prep AI Coach account. Visit the following link to reset your password:
    
    {reset_link}
    
    This link will expire in 1 hour.
    
    If you didn't request this reset, please ignore this email.
    
    Best regards,
    Interview Prep AI Coach Team
    """
    
    # In a real application, you would use asyncio.create_task or similar
    # For now, we'll just print the email content
    print(f"Password reset email for {email}:")
    print(f"Subject: Password Reset - Interview Prep AI Coach")
    print(f"Body: {text_body}")


def send_welcome_email(email: str, name: str):
    """Send welcome email after successful verification"""
    html_body = f"""
    <html>
        <body>
            <h2>Welcome to Interview Prep AI Coach!</h2>
            <p>Hi {name},</p>
            <p>Your email has been successfully verified. You can now access all features of our platform:</p>
            <ul>
                <li>AI-powered interview simulations</li>
                <li>Real-time body language analysis</li>
                <li>Tone and confidence scoring</li>
                <li>Progress tracking and analytics</li>
            </ul>
            <p><a href="http://localhost:4200/dashboard" style="background-color: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Start Practicing</a></p>
            <p>Best regards,<br>Interview Prep AI Coach Team</p>
        </body>
    </html>
    """
    
    text_body = f"""
    Welcome to Interview Prep AI Coach!
    
    Hi {name},
    
    Your email has been successfully verified. You can now access all features of our platform:
    
    - AI-powered interview simulations
    - Real-time body language analysis
    - Tone and confidence scoring
    - Progress tracking and analytics
    
    Visit http://localhost:4200/dashboard to start practicing.
    
    Best regards,
    Interview Prep AI Coach Team
    """
    
    print(f"Welcome email for {email}:")
    print(f"Subject: Welcome to Interview Prep AI Coach!")
    print(f"Body: {text_body}")