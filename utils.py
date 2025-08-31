import os
import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app, url_for
from flask_mail import Message
from extensions import mail, db
import re

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def generate_unique_filename(original_filename):
    """Generate unique filename while preserving extension"""
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    unique_id = str(uuid.uuid4())
    return f"{unique_id}.{ext}" if ext else unique_id

def calculate_file_hash(file_path):
    """Calculate SHA-256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def save_uploaded_file(file, upload_folder='uploads', subfolder=None):
    """Save uploaded file and return file info"""
    if not file or not allowed_file(file.filename):
        return None
    
    # Create upload directory if it doesn't exist
    if subfolder:
        upload_path = os.path.join(upload_folder, subfolder)
    else:
        upload_path = upload_folder
    
    os.makedirs(upload_path, exist_ok=True)
    
    # Generate unique filename
    original_filename = secure_filename(file.filename)
    unique_filename = generate_unique_filename(original_filename)
    file_path = os.path.join(upload_path, unique_filename)
    
    # Save file
    file.save(file_path)
    
    # Calculate file size and hash
    file_size = os.path.getsize(file_path)
    file_hash = calculate_file_hash(file_path)
    
    return {
        'filename': unique_filename,
        'original_filename': original_filename,
        'file_path': file_path,
        'file_size': file_size,
        'file_hash': file_hash,
        'mime_type': file.mimetype or 'application/octet-stream'
    }

def create_thumbnail(image_path, size=(300, 300)):
    """Create thumbnail for image files"""
    try:
        with Image.open(image_path) as img:
            img.thumbnail(size, Image.LANCZOS)
            
            # Create thumbnail filename
            base_name, ext = os.path.splitext(image_path)
            thumbnail_path = f"{base_name}_thumb{ext}"
            
            img.save(thumbnail_path, optimize=True, quality=85)
            return thumbnail_path
    except Exception as e:
        current_app.logger.error(f"Error creating thumbnail: {e}")
        return None

def send_email(to, subject, template, **kwargs):
    """Send email using Flask-Mail"""
    try:
        msg = Message(
            subject=f"[MedPeer] {subject}",
            recipients=[to],
            html=template,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Error sending email: {e}")
        return False

def send_verification_email(user):
    """Send email verification link"""
    token = generate_token()
    # Store token in database or cache
    verification_link = url_for('auth.verify_email', token=token, _external=True)
    
    template = f"""
    <h2>Welcome to MedPeer!</h2>
    <p>Please click the link below to verify your email address:</p>
    <p><a href="{verification_link}">Verify Email</a></p>
    <p>If you didn't create an account, please ignore this email.</p>
    """
    
    return send_email(user.email, "Email Verification", template)

def send_password_reset_email(user):
    """Send password reset email"""
    token = generate_token()
    # Store token in database or cache
    reset_link = url_for('auth.reset_password', token=token, _external=True)
    
    template = f"""
    <h2>Password Reset Request</h2>
    <p>Click the link below to reset your password:</p>
    <p><a href="{reset_link}">Reset Password</a></p>
    <p>If you didn't request this, please ignore this email.</p>
    """
    
    return send_email(user.email, "Password Reset", template)

def generate_token():
    """Generate secure random token"""
    return secrets.token_urlsafe(32)

def sanitize_html(content):
    """Sanitize HTML content to prevent XSS"""
    import bleach
    
    allowed_tags = [
        'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li',
        'h3', 'h4', 'h5', 'h6', 'blockquote', 'a'
    ]
    allowed_attributes = {
        'a': ['href', 'title'],
    }
    
    return bleach.clean(content, tags=allowed_tags, attributes=allowed_attributes, strip=True)

def extract_hashtags(text):
    """Extract hashtags from text"""
    hashtag_pattern = r'#\w+'
    return re.findall(hashtag_pattern, text)

def extract_mentions(text):
    """Extract @mentions from text"""
    mention_pattern = r'@\w+'
    return re.findall(mention_pattern, text)

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"

def time_ago(dt):
    """Return human-readable time ago string"""
    now = datetime.now(timezone.utc)
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "Just now"

def is_safe_url(target):
    """Check if URL is safe for redirect"""
    from urllib.parse import urlparse, urljoin
    from flask import request
    
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

def create_notification(user_id, message, notification_type, related_post_id=None, related_user_id=None):
    """Create a notification for a user"""
    from models import Notification
    
    notification = Notification(
        user_id=user_id,
        message=message,
        notification_type=notification_type,
        related_post_id=related_post_id,
        related_user_id=related_user_id
    )
    
    db.session.add(notification)
    db.session.commit()
    
    return notification

def get_user_notifications(user_id, unread_only=False, limit=20):
    """Get notifications for a user"""
    from models import Notification
    
    query = Notification.query.filter_by(user_id=user_id)
    
    if unread_only:
        query = query.filter_by(is_read=False)
    
    return query.order_by(Notification.created_at.desc()).limit(limit).all()

def mark_notifications_read(user_id, notification_ids=None):
    """Mark notifications as read"""
    from models import Notification
    
    query = Notification.query.filter_by(user_id=user_id, is_read=False)
    
    if notification_ids:
        query = query.filter(Notification.id.in_(notification_ids))
    
    query.update({Notification.is_read: True})
    db.session.commit()
