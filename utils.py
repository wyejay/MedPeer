import os
import re
import bleach
import datetime
from flask import url_for, current_app
from werkzeug.utils import secure_filename
from flask_mail import Message
from extensions import mail, db


# 1. Time ago helper
def time_ago(dt):
    now = datetime.datetime.utcnow()
    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return f"{int(seconds)}s ago"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    elif seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    else:
        return f"{int(seconds // 86400)}d ago"


# 2. File upload helper
def save_uploaded_file(file, folder="uploads"):
    if not file:
        return None
    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], folder, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)
    return f"/static/{folder}/{filename}"


# 3. HTML sanitizer
def sanitize_html(html):
    allowed_tags = bleach.sanitizer.ALLOWED_TAGS + ["p", "br", "span"]
    return bleach.clean(html, tags=allowed_tags, strip=True)


# 4. Email verification - Fixed import issue
def send_verification_email(user):
    from models import User  # Import here to avoid circular imports
    try:
        token = user.get_reset_token()
        msg = Message("Verify Your Account",
                      sender=current_app.config["MAIL_DEFAULT_SENDER"],
                      recipients=[user.email])
        link = url_for("auth.verify_email", token=token, _external=True)
        msg.body = f"Please verify your account: {link}"
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send verification email: {e}")
        return False


# 5. Password reset email - Fixed import issue
def send_password_reset_email(user):
    from models import User  # Import here to avoid circular imports
    try:
        token = user.get_reset_token()
        msg = Message("Password Reset Request",
                      sender=current_app.config["MAIL_DEFAULT_SENDER"],
                      recipients=[user.email])
        link = url_for("auth.reset_password", token=token, _external=True)
        msg.body = f"Reset your password here: {link}"
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send password reset email: {e}")
        return False


# 6. Safe URL check
def is_safe_url(target):
    from urllib.parse import urlparse, urljoin
    try:
        ref_url = urlparse(current_app.config.get("SERVER_NAME", "localhost"))
        test_url = urlparse(urljoin(ref_url.geturl(), target))
        return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc
    except Exception:
        return False


# 7. Create notification - Fixed to use correct model
def create_notification(user_id, message, notification_type="info", related_post_id=None, related_user_id=None):
    from models import Notification  # Import here to avoid circular imports
    try:
        notif = Notification(
            user_id=user_id, 
            message=message,
            notification_type=notification_type,
            related_post_id=related_post_id,
            related_user_id=related_user_id,
            created_at=datetime.datetime.utcnow()
        )
        db.session.add(notif)
        db.session.commit()
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to create notification: {e}")
        db.session.rollback()
        return False


# 8. Get user notifications - Fixed to use correct model
def get_user_notifications(user_id, limit=10):
    from models import Notification  # Import here to avoid circular imports
    try:
        return (Notification.query.filter_by(user_id=user_id)
                .order_by(Notification.created_at.desc())
                .limit(limit)
                .all())
    except Exception as e:
        current_app.logger.error(f"Failed to get notifications: {e}")
        return []


# 9. Extract hashtags
def extract_hashtags(text):
    if not text:
        return []
    return re.findall(r"#(\w+)", text)


# 10. Validate file extension
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


# 11. Format file size
def format_file_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ["B", "KB", "MB", "GB", "TB"]
    i = int((size_bytes).bit_length() / 10)
    p = pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"
