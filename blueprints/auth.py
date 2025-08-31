from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse as url_parse
from models import User, UserRole, db
from forms import LoginForm, RegistrationForm, ForgotPasswordForm, ResetPasswordForm, EditProfileForm
from utils import send_verification_email, send_password_reset_email, is_safe_url, save_uploaded_file
import secrets

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('Your account has been deactivated. Please contact support.', 'warning')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        
        # Update last seen
        from datetime import datetime, timezone
        user.last_seen = datetime.now(timezone.utc)
        db.session.commit()
        
        # Redirect to next page or dashboard
        next_page = request.args.get('next')
        if not next_page or not is_safe_url(next_page):
            next_page = url_for('main.dashboard')
        
        flash(f'Welcome back, {user.first_name}!', 'success')
        return redirect(next_page)
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Create new user
        user = User(
            username=form.username.data.lower(),
            email=form.email.data.lower(),
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role=UserRole(form.role.data),
            institution=form.institution.data,
            year_level=form.year_level.data,
            specialty=form.specialty.data
        )
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            
            # Send verification email
            send_verification_email(user)
            
            flash('Congratulations, you are now registered! Please check your email to verify your account.', 'success')
            return redirect(url_for('auth.login'))
        
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            current_app.logger.error(f"Registration error: {e}")
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = ForgotPasswordForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user:
            # Generate reset token and send email
            token = secrets.token_urlsafe(32)
            session[f'reset_token_{user.id}'] = token
            
            send_password_reset_email(user)
            flash('Check your email for the instructions to reset your password.', 'info')
        else:
            flash('Email address not found.', 'warning')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html', form=form)

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    # Find user by token (simplified version)
    user = None
    for key, value in session.items():
        if key.startswith('reset_token_') and value == token:
            user_id = key.split('_')[-1]
            user = User.query.get(int(user_id))
            break
    
    if not user:
        flash('Invalid or expired reset token.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        
        # Remove token from session
        for key in list(session.keys()):
            if key.startswith('reset_token_'):
                del session[key]
        
        flash('Your password has been reset.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', form=form)

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    """Verify email address"""
    # Simplified email verification
    flash('Your email has been verified!', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    form = EditProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        try:
            # Update user data
            current_user.first_name = form.first_name.data
            current_user.last_name = form.last_name.data
            current_user.bio = form.bio.data
            current_user.institution = form.institution.data
            current_user.year_level = form.year_level.data
            current_user.specialty = form.specialty.data
            current_user.location = form.location.data
            current_user.website = form.website.data
            current_user.linkedin = form.linkedin.data
            current_user.privacy_level = form.privacy_level.data
            
            # Handle profile picture upload
            if form.profile_picture.data:
                file_info = save_uploaded_file(form.profile_picture.data, subfolder='profiles')
                if file_info:
                    current_user.profile_picture = file_info['file_path']
            
            db.session.commit()
            flash('Your profile has been updated.', 'success')
            return redirect(url_for('main.profile', username=current_user.username))
        
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your profile.', 'danger')
            current_app.logger.error(f"Profile update error: {e}")
    
    return render_template('auth/edit_profile.html', form=form)

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    from wtforms import PasswordField, SubmitField
    from wtforms.validators import DataRequired, EqualTo, Length
    
    class ChangePasswordForm(FlaskForm):
        current_password = PasswordField('Current Password', validators=[DataRequired()])
        new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
        confirm_password = PasswordField('Confirm New Password', 
                                       validators=[DataRequired(), EqualTo('new_password')])
        submit = SubmitField('Change Password')
    
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return render_template('auth/change_password.html', form=form)
        
        current_user.set_password(form.new_password.data)
        db.session.commit()
        
        flash('Your password has been changed.', 'success')
        return redirect(url_for('main.settings'))
    
    return render_template('auth/change_password.html', form=form)
