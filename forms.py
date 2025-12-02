from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from models import User

class SignupForm(FlaskForm):
    name = StringField('Full Name', validators=[
        DataRequired(message='Name is required'),
        Length(min=2, max=100, message='Name must be between 2 and 100 characters')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=8, message='Password must be at least 8 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password'),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Sign Up')
    
    def validate_email(self, field):
        user = User.query.filter_by(email=field.data.lower()).first()
        if user and user.email_verified:
            raise ValidationError('An account with this email already exists. Please log in instead.')


class VerifyOTPForm(FlaskForm):
    otp = StringField('Verification Code', validators=[
        DataRequired(message='Verification code is required'),
        Length(min=6, max=6, message='Verification code must be 6 digits')
    ])
    submit = SubmitField('Verify')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required')
    ])
    submit = SubmitField('Log In')


class ResendOTPForm(FlaskForm):
    submit = SubmitField('Resend Code')
