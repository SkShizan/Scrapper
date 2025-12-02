import io
import os
import pandas as pd
from functools import wraps
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, User, Lead
from forms import SignupForm, VerifyOTPForm, LoginForm, ResendOTPForm
from email_service import email_service

from scrapers.google import GoogleScraper
from scrapers.social import SocialMediaScraper
from scrapers.yellow_pages import YellowPagesScraper

app = Flask(__name__)
app.config.from_object(Config)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///leadscaper.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def approved_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not current_user.email_verified:
            flash('Please verify your email first.', 'warning')
            return redirect(url_for('verify_otp'))
        if not current_user.is_approved:
            return render_template('pending_approval.html')
        if not current_user.is_active:
            flash('Your account has been disabled. Please contact administrator.', 'error')
            logout_user()
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not current_user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        if current_user.can_access_app():
            return redirect(url_for('index'))
        if not current_user.email_verified:
            return redirect(url_for('verify_otp'))
        return redirect(url_for('index'))
    
    form = SignupForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data.lower(),
            name=form.name.data
        )
        user.set_password(form.password.data)
        otp = user.generate_otp()
        
        db.session.add(user)
        db.session.commit()
        
        if email_service.is_configured():
            email_service.send_otp_email(user.email, otp, user.name)
            flash('Account created! Please check your email for the verification code.', 'success')
        else:
            flash(f'Account created! SMTP not configured. Your OTP is: {otp}', 'warning')
        
        login_user(user)
        session['pending_verification_user_id'] = user.id
        return redirect(url_for('verify_otp'))
    
    return render_template('signup.html', form=form)


@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if not current_user.is_authenticated:
        user_id = session.get('pending_verification_user_id')
        if user_id:
            user = User.query.get(user_id)
            if user:
                login_user(user)
        else:
            return redirect(url_for('login'))
    
    if current_user.email_verified:
        if current_user.can_access_app():
            return redirect(url_for('index'))
        return render_template('pending_approval.html')
    
    form = VerifyOTPForm()
    resend_form = ResendOTPForm()
    
    if form.validate_on_submit():
        if current_user.verify_otp(form.otp.data):
            db.session.commit()
            session.pop('pending_verification_user_id', None)
            flash('Email verified successfully! Please wait for admin approval.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid or expired verification code.', 'error')
    
    return render_template('verify_otp.html', form=form, resend_form=resend_form)


@app.route('/resend-otp', methods=['POST'])
def resend_otp():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    if current_user.email_verified:
        return redirect(url_for('index'))
    
    otp = current_user.generate_otp()
    db.session.commit()
    
    if email_service.is_configured():
        email_service.send_otp_email(current_user.email, otp, current_user.name)
        flash('A new verification code has been sent to your email.', 'success')
    else:
        flash(f'SMTP not configured. Your new OTP is: {otp}', 'warning')
    
    return redirect(url_for('verify_otp'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if not current_user.email_verified:
            return redirect(url_for('verify_otp'))
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been disabled. Please contact administrator.', 'error')
                return render_template('login.html', form=form)
            
            login_user(user)
            
            if not user.email_verified:
                return redirect(url_for('verify_otp'))
            
            next_page = request.args.get('next')
            flash('Logged in successfully!', 'success')
            return redirect(next_page if next_page else url_for('index'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/')
@login_required
@approved_required
def index():
    return render_template('index.html')


@app.route('/search', methods=['POST'])
@login_required
@approved_required
def handle_search():
    data = request.json
    query = data.get('query')
    location = data.get('location')
    api_key = data.get('apiKey')
    cx = data.get('cx')
    platform = data.get('platform', 'google')
    page = int(data.get('page', 1))

    if not query or not location:
        return jsonify({"error": "Missing query or location."}), 400

    scraper = None
    new_leads = []
    meta = {"current_page": 1, "has_next": False}

    if platform == 'yellowpages':
        scraper = YellowPagesScraper()
        result_data = scraper.search(query, location, api_key, cx, page=page)

        if isinstance(result_data, dict) and "error" in result_data:
            return jsonify(result_data), 400

        new_leads = result_data.get('leads', [])
        meta = result_data.get('meta', {})

    elif platform in ['linkedin', 'facebook', 'instagram']:
        scraper = SocialMediaScraper(platform)
        new_leads = scraper.search(query, location, api_key, cx)
        if isinstance(new_leads, dict) and "error" in new_leads:
            return jsonify(new_leads), 400
    else:
        scraper = GoogleScraper()
        new_leads = scraper.search(query, location, api_key, cx)
        if isinstance(new_leads, dict) and "error" in new_leads:
            return jsonify(new_leads), 400

    for lead_data in new_leads:
        lead = Lead(
            user_id=current_user.id,
            name=lead_data.get('Name', 'Unknown'),
            email=lead_data.get('Email'),
            website=lead_data.get('Website'),
            location=lead_data.get('Location'),
            source=lead_data.get('Source')
        )
        db.session.add(lead)
    
    db.session.commit()

    return jsonify({
        "leads": new_leads,
        "meta": meta
    })


@app.route('/download')
@login_required
@approved_required
def handle_download():
    leads = Lead.query.filter_by(user_id=current_user.id).all()
    
    if not leads:
        flash('No leads to download.', 'warning')
        return redirect(url_for('index'))

    leads_data = [lead.to_dict() for lead in leads]
    df = pd.DataFrame(leads_data)

    columns = ['Name', 'Email', 'Website', 'Location', 'Source']
    for col in columns:
        if col not in df.columns:
            df[col] = ''

    df = df[columns]

    mem_file = io.BytesIO()
    df.to_csv(mem_file, index=False, encoding='utf-8')
    mem_file.seek(0)

    return send_file(
        mem_file,
        mimetype='text/csv',
        as_attachment=True,
        download_name='leads_export.csv'
    )


@app.route('/clear-leads', methods=['POST'])
@login_required
@approved_required
def clear_leads():
    Lead.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({"success": True, "message": "All leads cleared."})


@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    pending_users = User.query.filter_by(email_verified=True, is_approved=False).all()
    all_users = User.query.filter(User.id != current_user.id).order_by(User.created_at.desc()).all()
    return render_template('admin.html', pending_users=pending_users, all_users=all_users)


@app.route('/admin/approve/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    
    if email_service.is_configured():
        email_service.send_approval_notification(user.email, user.name, approved=True)
    
    flash(f'User {user.email} has been approved.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/reject/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def reject_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if email_service.is_configured():
        email_service.send_approval_notification(user.email, user.name, approved=False)
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {user.email} has been rejected and removed.', 'info')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/toggle-status/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'enabled' if user.is_active else 'disabled'
    flash(f'User {user.email} has been {status}.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/toggle-admin/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_admin_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot change your own admin status.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    status = 'granted' if user.is_admin else 'revoked'
    flash(f'Admin access {status} for {user.email}.', 'success')
    return redirect(url_for('admin_dashboard'))


def create_superuser():
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    
    existing = User.query.filter_by(email=admin_email).first()
    if not existing:
        admin = User(
            email=admin_email,
            name='Administrator',
            email_verified=True,
            is_approved=True,
            is_admin=True
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print(f"Superuser created: {admin_email}")
    else:
        print(f"Superuser already exists: {admin_email}")


with app.app_context():
    db.create_all()
    create_superuser()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
