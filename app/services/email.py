import smtplib
from email.message import EmailMessage
from app.config import settings

def send_otp_email(email: str, otp: str):
    print(f"[DEV] OTP to {email}: {otp}")  # just print it for now
    return True


#for production:
# def send_otp_email(to_email: str, otp: str):
#     msg = EmailMessage()
#     msg["Subject"] = "Your OTP Code"
#     msg["From"] = settings.EMAIL_USER
#     msg["To"] = to_email
#     msg.set_content(f"Your OTP is {otp}. It will expire in 10 minutes.")

#     with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
#         server.starttls()
#         server.login(settings.EMAIL_USER, settings.EMAIL_PASS)
#         server.send_message(msg)
