from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import User, Post, Comment, File, ContentFlag, AdminAction, SiteSettings, db
from forms import AdminActionForm
from utils import time_ago
from datetime import datetime, timezone, timedelta

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Administrator access required.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with site metrics"""
    # Get site statistics
    total_users = User.query.filter_by(is_active=True).count()
    total_posts = Post.query.filter_by(is_deleted=False).count()
    total_files = File.query.filter_by(is_deleted=False).count()
    
    # Recent activity
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_posts = Post.query.filter_by(is_deleted=False).order_by(Post.created_at.desc()).limit(10).all()
    
    # Pending flags
    pending_flags = ContentFlag.query.filter_by(status='pending').count()
    
    # Active users (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    active_users = User.query.filter(User.last_seen >= thirty_days_ago).count()
    
    stats = {
        'total_users': total_users,
        'total_posts': total_posts,
        'total_files': total_files,
        'pending_flags': pending_flags,
        'active_users': active_users
    }
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         recent_users=recent_users,
                         recent_posts=recent_posts,
                         time_ago=time_ago)

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    """User management page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', 'all')
    
    query = User.query
    
    if search:
        query = query.filter(
            db.or_(
                User.username.contains(search),
                User.email.contains(search),
                User.first_name.contains(search),
                User.last_name.contains(search)
            )
        )
    
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)
    elif status == 'admin':
        query = query.filter_by(is_admin=True)
    
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/users.html', 
                         users=users, 
                         search=search, 
                         status=status,
                         time_ago=time_ago)

@admin_bp.route('/user/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    """User detail page for admin"""
    user = User.query.get_or_404(user_id)
    
    # Get user's posts and activity
    posts = Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc()).limit(10).all()
    comments = Comment.query.filter_by(user_id=user_id).order_by(Comment.created_at.desc()).limit(10).all()
    
    # Get admin actions taken on this user
    actions = AdminAction.query.filter_by(target_user_id=user_id).order_by(
        AdminAction.created_at.desc()
    ).limit(10).all()
    
    form = AdminActionForm()
    
    return render_template('admin/user_detail.html', 
                         user=user, 
                         posts=posts, 
                         comments=comments,
                         actions=actions,
                         form=form,
                         time_ago=time_ago)

@admin_bp.route('/user/<int:user_id>/action', methods=['POST'])
@login_required
@admin_required
def user_action(user_id):
    """Take admin action on a user"""
    user = User.query.get_or_404(user_id)
    form = AdminActionForm()
    
    if form.validate_on_submit():
        try:
            action_type = form.action_type.data
            description = form.description.data
            
            # Record admin action
            admin_action = AdminAction(
                action_type=action_type,
                description=description,
                admin_id=current_user.id,
                target_user_id=user_id
            )
            
            db.session.add(admin_action)
            
            # Apply the action
            if action_type == 'suspend':
                user.is_active = False
                flash(f'User {user.username} has been suspended.', 'warning')
            elif action_type == 'ban':
                user.is_active = False
                flash(f'User {user.username} has been banned.', 'danger')
            elif action_type == 'warn':
                # Create notification for user
                from utils import create_notification
                create_notification(
                    user_id,
                    f"Warning from administrator: {description}",
                    "admin"
                )
                flash(f'Warning sent to {user.username}.', 'info')
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while taking the action.', 'danger')
            current_app.logger.error(f"Admin action error: {e}")
    
    return redirect(url_for('admin.user_detail', user_id=user_id))

@admin_bp.route('/posts')
@login_required
@admin_required
def manage_posts():
    """Post management page"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    search = request.args.get('search', '')
    
    query = Post.query
    
    if status == 'flagged':
        query = query.filter_by(is_flagged=True)
    elif status == 'deleted':
        query = query.filter_by(is_deleted=True)
    elif status == 'active':
        query = query.filter_by(is_deleted=False, is_flagged=False)
    
    if search:
        query = query.filter(
            db.or_(
                Post.title.contains(search),
                Post.content.contains(search)
            )
        )
    
    posts = query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/posts.html', 
                         posts=posts, 
                         status=status, 
                         search=search,
                         time_ago=time_ago)

@admin_bp.route('/post/<int:post_id>/action', methods=['POST'])
@login_required
@admin_required
def post_action(post_id):
    """Take admin action on a post"""
    post = Post.query.get_or_404(post_id)
    action = request.form.get('action')
    reason = request.form.get('reason', '')
    
    try:
        # Record admin action
        admin_action = AdminAction(
            action_type=f"post_{action}",
            description=reason,
            admin_id=current_user.id,
            target_post_id=post_id,
            target_user_id=post.user_id
        )
        
        db.session.add(admin_action)
        
        if action == 'delete':
            post.is_deleted = True
            flash('Post has been deleted.', 'info')
        elif action == 'restore':
            post.is_deleted = False
            post.is_flagged = False
            flash('Post has been restored.', 'success')
        elif action == 'clear_flag':
            post.is_flagged = False
            flash('Flag has been cleared.', 'info')
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while taking the action.', 'danger')
        current_app.logger.error(f"Admin post action error: {e}")
    
    return redirect(url_for('admin.manage_posts'))

@admin_bp.route('/flags')
@login_required
@admin_required
def manage_flags():
    """Content flag management"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'pending')
    
    query = ContentFlag.query
    
    if status != 'all':
        query = query.filter_by(status=status)
    
    flags = query.order_by(ContentFlag.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/flags.html', 
                         flags=flags, 
                         status=status,
                         time_ago=time_ago)

@admin_bp.route('/flag/<int:flag_id>/review', methods=['POST'])
@login_required
@admin_required
def review_flag(flag_id):
    """Review a content flag"""
    flag = ContentFlag.query.get_or_404(flag_id)
    action = request.form.get('action')
    
    try:
        flag.reviewed_by = current_user.id
        flag.reviewed_at = datetime.now(timezone.utc)
        
        if action == 'dismiss':
            flag.status = 'dismissed'
            flash('Flag has been dismissed.', 'info')
        elif action == 'act':
            flag.status = 'acted'
            
            # Take action based on flag type
            if flag.post_id:
                post = Post.query.get(flag.post_id)
                if post:
                    post.is_deleted = True
            
            flash('Flag has been acted upon.', 'success')
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while reviewing the flag.', 'danger')
        current_app.logger.error(f"Flag review error: {e}")
    
    return redirect(url_for('admin.manage_flags'))

@admin_bp.route('/settings')
@login_required
@admin_required
def site_settings():
    """Site settings management"""
    settings = SiteSettings.query.all()
    return render_template('admin/settings.html', settings=settings)

@admin_bp.route('/settings/update', methods=['POST'])
@login_required
@admin_required
def update_settings():
    """Update site settings"""
    for key, value in request.form.items():
        if key.startswith('setting_'):
            setting_key = key.replace('setting_', '')
            setting = SiteSettings.query.filter_by(key=setting_key).first()
            
            if setting:
                setting.value = value
                setting.updated_at = datetime.now(timezone.utc)
            else:
                setting = SiteSettings(key=setting_key, value=value)
                db.session.add(setting)
    
    db.session.commit()
    flash('Settings have been updated.', 'success')
    return redirect(url_for('admin.site_settings'))

@admin_bp.route('/logs')
@login_required
@admin_required
def admin_logs():
    """View admin action logs"""
    page = request.args.get('page', 1, type=int)
    
    logs = AdminAction.query.order_by(AdminAction.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    return render_template('admin/logs.html', logs=logs, time_ago=time_ago)

@admin_bp.route('/stats/api')
@login_required
@admin_required
def stats_api():
    """API endpoint for dashboard statistics"""
    # Get data for charts/graphs
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    
    # User registrations over time
    user_data = db.session.query(
        db.func.date(User.created_at).label('date'),
        db.func.count(User.id).label('count')
    ).filter(
        User.created_at >= thirty_days_ago
    ).group_by(
        db.func.date(User.created_at)
    ).all()
    
    # Posts over time
    post_data = db.session.query(
        db.func.date(Post.created_at).label('date'),
        db.func.count(Post.id).label('count')
    ).filter(
        Post.created_at >= thirty_days_ago
    ).group_by(
        db.func.date(Post.created_at)
    ).all()
    
    return jsonify({
        'user_registrations': [{'date': str(d.date), 'count': d.count} for d in user_data],
        'posts_created': [{'date': str(d.date), 'count': d.count} for d in post_data]
    })
