from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from extensions import db
from models import Post, Comment, Notification
from datetime import datetime

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/posts", methods=["GET"])
@login_required
def get_posts():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return jsonify([{
        "id": p.id,
        "title": p.title,
        "content": p.content,
        "author": p.author.username,
        "created_at": p.created_at.isoformat()
    } for p in posts])

@api_bp.route("/posts", methods=["POST"])
@login_required
def create_post():
    data = request.json
    post = Post(
        title=data.get("title"),
        content=data.get("content"),
        user_id=current_user.id,
        created_at=datetime.utcnow()
    )
    db.session.add(post)
    db.session.commit()
    return jsonify({"message": "Post created", "id": post.id}), 201

@api_bp.route("/comments", methods=["POST"])
@login_required
def add_comment():
    data = request.json
    comment = Comment(
        content=data.get("content"),
        post_id=data.get("post_id"),
        user_id=current_user.id,
        created_at=datetime.utcnow()
    )
    db.session.add(comment)
    db.session.commit()
    return jsonify({"message": "Comment added", "id": comment.id}), 201

@api_bp.route("/notifications", methods=["GET"])
@login_required
def get_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return jsonify([{
        "id": n.id,
        "message": n.message,
        "type": n.notification_type,
        "created_at": n.created_at.isoformat(),
        "is_read": n.is_read
    } for n in notifications])

@api_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    notification.is_read = True
    db.session.commit()
    return jsonify({"message": "Notification marked as read"})
