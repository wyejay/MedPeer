from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import User, Post, Comment, AdminAction, ContentFlag, SiteSettings
from datetime import datetime

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")

def admin_required(func):
    """Restrict access to admin users only."""
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("main.index"))
        return func(*args, **kwargs)
    return wrapper

@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    users = User.query.count()
    posts = Post.query.count()
    comments = Comment.query.count()
    flags = ContentFlag.query.filter_by(status="pending").count()
    return render_template("admin/dashboard.html", users=users, posts=posts, comments=comments, flags=flags)

@admin_bp.route("/flags")
@login_required
@admin_required
def view_flags():
    flags = ContentFlag.query.order_by(ContentFlag.created_at.desc()).all()
    return render_template("admin/flags.html", flags=flags)

@admin_bp.route("/flags/<int:flag_id>/review", methods=["POST"])
@login_required
@admin_required
def review_flag(flag_id):
    flag = ContentFlag.query.get_or_404(flag_id)
    action = request.form.get("action")
    flag.status = action
    flag.reviewed_by = current_user.id
    flag.reviewed_at = datetime.utcnow()
    
    admin_action = AdminAction(
        action_type="review_flag",
        description=f"Reviewed flag {flag.id} with action {action}",
        admin_id=current_user.id,
        created_at=datetime.utcnow()
    )
    db.session.add(admin_action)
    db.session.commit()
    flash("Flag reviewed successfully.", "success")
    return redirect(url_for("admin.view_flags"))

@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
@admin_required
def settings():
    if request.method == "POST":
        for key, value in request.form.items():
            setting = SiteSettings.query.filter_by(key=key).first()
            if setting:
                setting.value = value
                setting.updated_at = datetime.utcnow()
            else:
                setting = SiteSettings(key=key, value=value, updated_at=datetime.utcnow())
                db.session.add(setting)
        db.session.commit()
        flash("Settings updated successfully.", "success")
        return redirect(url_for("admin.settings"))
    
    settings = SiteSettings.query.all()
    return render_template("admin/settings.html", settings=settings)
