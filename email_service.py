import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

class EmailService:
    def __init__(self):
        self.smtp_host = os.environ.get('SMTP_HOST', 'smtp.hostinger.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.smtp_user = os.environ.get('SMTP_USER', 'info@thenetvista.com')
        self.smtp_password = os.environ.get('SMTP_PASSWORD', 'Nafis@983168')
        self.from_email = os.environ.get('SMTP_FROM_EMAIL', self.smtp_user)
        self.from_name = os.environ.get('SMTP_FROM_NAME', 'Lead Scraper')
    
    def is_configured(self):
        return bool(self.smtp_user and self.smtp_password)
    
    def send_email(self, to_email, subject, html_content, text_content=None):
        if not self.is_configured():
            print("SMTP not configured. Email not sent.")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            if text_content:
                part1 = MIMEText(text_content, 'plain')
                msg.attach(part1)
            
            part2 = MIMEText(html_content, 'html')
            msg.attach(part2)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, to_email, msg.as_string())
            
            print(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False
    
    def send_otp_email(self, to_email, otp, name):
        subject = "Your Verification Code - Lead Scraper"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; background-color: #FFFBF2; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; padding: 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #B77466; margin: 0; font-size: 24px; }}
                .otp-box {{ background-color: #FDF8F5; border: 2px solid #E2B59A; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0; }}
                .otp-code {{ font-size: 36px; font-weight: bold; color: #B77466; letter-spacing: 8px; }}
                .message {{ color: #4F3E3A; line-height: 1.6; }}
                .footer {{ margin-top: 30px; text-align: center; color: #957C62; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Lead Scraper</h1>
                </div>
                <div class="message">
                    <p>Hello {name},</p>
                    <p>Thank you for signing up! Please use the verification code below to complete your registration:</p>
                </div>
                <div class="otp-box">
                    <div class="otp-code">{otp}</div>
                </div>
                <div class="message">
                    <p>This code will expire in 10 minutes.</p>
                    <p>After verification, your account will need to be approved by an administrator before you can access the application.</p>
                    <p>If you didn't request this code, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; Lead Scraper - All rights reserved</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hello {name},
        
        Thank you for signing up for Lead Scraper!
        
        Your verification code is: {otp}
        
        This code will expire in 10 minutes.
        
        After verification, your account will need to be approved by an administrator before you can access the application.
        
        If you didn't request this code, please ignore this email.
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_approval_notification(self, to_email, name, approved=True):
        if approved:
            subject = "Account Approved - Lead Scraper"
            status_message = "Your account has been approved! You can now log in and start using the application."
            status_color = "#198754"
        else:
            subject = "Account Status Update - Lead Scraper"
            status_message = "Unfortunately, your account request has been declined. Please contact the administrator for more information."
            status_color = "#dc3545"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; background-color: #FFFBF2; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; padding: 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #B77466; margin: 0; font-size: 24px; }}
                .status-box {{ background-color: {status_color}20; border: 2px solid {status_color}; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0; }}
                .status-text {{ font-size: 18px; font-weight: bold; color: {status_color}; }}
                .message {{ color: #4F3E3A; line-height: 1.6; }}
                .footer {{ margin-top: 30px; text-align: center; color: #957C62; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Lead Scraper</h1>
                </div>
                <div class="message">
                    <p>Hello {name},</p>
                </div>
                <div class="status-box">
                    <div class="status-text">{status_message}</div>
                </div>
                <div class="footer">
                    <p>&copy; Lead Scraper - All rights reserved</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)


email_service = EmailService()
