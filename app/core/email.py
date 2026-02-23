import secrets
import smtplib, random, string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings


def generate_otp(length: int=6) -> str:
    return ''.join(secrets.choice(string.digits) for _ in range(length))




def send_otp_email(to_email: str, otp_code: str, username: str) -> bool:
    subject = 'Verify Your Account - OTP Code'
    body = f'''
Hello {username},
 
Your OTP verification code is:
 
    *** {otp_code} ***
 
This code expires in {settings.OTP_EXPIRE_MINUTES} minutes.
 
If you did not register, please ignore this email.
 
Best regards,
Team Binary
    '''
    msg = MIMEMultipart()
    msg['From'] = settings.EMAIL_FROM
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain')) #we can use html body, then we need replace plain -> html. for better text or email using html formate
    
    try:
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.starttls()
            server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f'Email send error: {e}')
        return False
    




def send_password_reset_email(to_email: str, otp_code: str, username: str) -> bool:
    subject = 'Password Reset Request - OTP Code'
    body = f'''
Hello {username},
You requested a password reset. Your OTP code is:

    *** {otp_code} ***
This code expires in {settings.RESET_OTP_EXPIRE_MINUTES} minutes.
If you did not request a password reset, please ignore this email.
Best regards,
Team Binary
    '''
    msg = MIMEMultipart()
    msg['From'] = settings.EMAIL_FROM
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.starttls()
            server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f'Email send error: {e}')
        return False
        
