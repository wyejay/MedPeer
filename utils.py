import os
import re
import bleach
import datetime
from flask import url_for, current_app
from werkzeug.utils import secure_filename
from flask_mail import Message
from extensions import mail, db
from models import Notification, User


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


# 4. Email verification
def send_verification_email(user):
    token = user.get_reset_token()
    msg = Message("Verify Your Account",
                  sender=current_app.config["MAIL_DEFAULT_SENDER"],
                  recipients=[user.email])
    link = url_for("auth.verify_email", token=token, _external=True)
    msg.body = f"Please verify your account: {link}"
    mail.send(msg)


# 5. Password reset email
def send_password_reset_email(user):
    token = user.get_reset_token()
    msg = Message("Password Reset Request",
                  sender=current_app.config["MAIL_DEFAULT_SENDER"],
                  recipients=[user.email])
    link = url_for("auth.reset_password", token=token, _external=True)
    msg.body = f"Reset your password here: {link}"
    mail.send(msg)


# 6. Safe URL check
def is_safe_url(target):
    from urllib.parse import urlparse, urljoin
    ref_url = urlparse(current_app.config["SERVER_NAME"] or "")
    test_url = urlparse(urljoin(ref_url.geturl(), target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


# 7. Create notification
def create_notification(user_id, message):
    notif = Notification(user_id=user_id, message=message, timestamp=datetime.datetime.utcnow())
    db.session.add(notif)
    db.session.commit()


# 8. Get user notifications
def get_user_notifications(user_id, limit=10):
    return (Notification.query.filter_by(user_id=user_id)
            .order_by(Notification.timestamp.desc())
            .limit(limit)
            .all())


# 9. Extract hashtags
def extract_hashtags(text):
    return re.findall(r"#(\w+)", text)
