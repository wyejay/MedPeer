from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_, and_
from models import User, Post, Tag, File, Notification, db
from forms import SearchForm, ContactForm
from utils import time_ago, get_user_notifications

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home/Landing page"""
    # Get featured posts for non-authenticated users
    featured_posts = []
    if not current_user.is_authenticated:
        featured_posts = Post.query.filter_by(is_deleted=False).order_by(Post.created_at.desc()).limit(6).all()
    
    return render_template('index.html', featured_posts=featured_posts)

@main_bp.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page"""
    form = ContactForm()
    
    if form.validate_on_submit():
        # In a real app, you would send this to admin email or save to database
        flash('Thank you for your message. We will get back to you soon!', 'success')
        return redirect(url_for('main.contact'))
    
    return render_template('contact.html', form=form)

@main_bp.route('/terms')
def terms():
    """Terms of Service page"""
    return render_template('legal/terms.html')

@main_bp.route('/privacy')
def privacy():
    """Privacy Policy page"""
    return render_template('legal/privacy.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with feed"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Get posts for feed (own posts + followed users)
    posts = current_user.get_feed_posts().paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get notifications
    notifications = get_user_notifications(current_user.id, unread_only=True, limit=5)
    
    # Get suggested users to follow
    suggested_users = User.query.filter(
        and_(
            User.id != current_user.id,
            ~User.followers.contains(current_user)
        )
    ).limit(5).all()
    
    return render_template('dashboard.html', 
                         posts=posts, 
                         notifications=notifications,
                         suggested_users=suggested_users,
                         time_ago=time_ago)

@main_bp.route('/search')
def search():
    """Search page"""
    form = SearchForm()
    results = []
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    if query:
        form.query.data = query
        form.search_type.data = search_type
        
        if search_type == 'posts' or search_type == 'all':
            # Search posts
            post_query = Post.query.filter(
                and_(
                    Post.is_deleted == False,
                    or_(
                        Post.title.contains(query),
                        Post.content.contains(query)
                    )
                )
            ).order_by(Post.created_at.desc())
            
            if search_type == 'posts':
                results = post_query.paginate(page=page, per_page=per_page, error_out=False)
            else:
                results.extend(post_query.limit(10).all())
        
        if search_type == 'users' or search_type == 'all':
            # Search users
            user_query = User.query.filter(
                and_(
                    User.is_active == True,
                    or_(
                        User.username.contains(query),
                        User.first_name.contains(query),
                        User.last_name.contains(query),
                        User.institution.contains(query)
                    )
                )
            ).order_by(User.created_at.desc())
            
            if search_type == 'users':
                results = user_query.paginate(page=page, per_page=per_page, error_out=False)
            elif search_type == 'all':
                results.extend(user_query.limit(10).all())
        
        if search_type == 'files' or search_type == 'all':
            # Search files
            file_query = File.query.filter(
                and_(
                    File.is_deleted == False,
                    File.original_filename.contains(query)
                )
            ).order_by(File.created_at.desc())
            
            if search_type == 'files':
                results = file_query.paginate(page=page, per_page=per_page, error_out=False)
            elif search_type == 'all':
                results.extend(file_query.limit(10).all())
    
    return render_template('search.html', form=form, results=results, query=query, search_type=search_type)

@main_bp.route('/profile/<username>')
def profile(username):
    """User profile page"""
    user = User.query.filter_by(username=username).first_or_404()
    
    # Check privacy settings
    can_view = True
    if user.privacy_level.value == 'private' and current_user != user:
        can_view = False
    elif user.privacy_level.value == 'followers' and current_user != user:
        if not current_user.is_authenticated or not current_user.is_following(user):
            can_view = False
    
    if not can_view:
        flash('This profile is private.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    # Get user's posts
    page = request.args.get('page', 1, type=int)
    posts = user.get_posts().paginate(page=page, per_page=10, error_out=False)
    
    return render_template('profile.html', user=user, posts=posts, time_ago=time_ago)

@main_bp.route('/settings')
@login_required
def settings():
    """User settings page"""
    return render_template('settings.html')

@main_bp.route('/notifications')
@login_required
def notifications():
    """User notifications page"""
    page = request.args.get('page', 1, type=int)
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('notifications.html', notifications=notifications, time_ago=time_ago)

@main_bp.route('/follow/<username>')
@login_required
def follow(username):
    """Follow a user"""
    user = User.query.filter_by(username=username).first_or_404()
    
    if user == current_user:
        flash('You cannot follow yourself!', 'warning')
        return redirect(url_for('main.profile', username=username))
    
    current_user.follow(user)
    db.session.commit()
    flash(f'You are now following {user.get_full_name()}!', 'success')
    
    return redirect(url_for('main.profile', username=username))

@main_bp.route('/unfollow/<username>')
@login_required
def unfollow(username):
    """Unfollow a user"""
    user = User.query.filter_by(username=username).first_or_404()
    
    if user == current_user:
        flash('You cannot unfollow yourself!', 'warning')
        return redirect(url_for('main.profile', username=username))
    
    current_user.unfollow(user)
    db.session.commit()
    flash(f'You are no longer following {user.get_full_name()}.', 'info')
    
    return redirect(url_for('main.profile', username=username))

# Context processors to make functions available in templates
@main_bp.app_context_processor
def utility_processor():
    return dict(time_ago=time_ago)
