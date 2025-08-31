from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models import User, Post, Comment, Message, File, Tag, db
from utils import save_uploaded_file, sanitize_html, create_notification
from functools import wraps
import jwt
from datetime import datetime, timezone, timedelta

api_bp = Blueprint('api', __name__)

def api_auth_required(f):
    """API authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def paginate_query(query, page=1, per_page=20):
    """Helper function to paginate queries"""
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        'items': paginated.items,
        'page': paginated.page,
        'pages': paginated.pages,
        'per_page': paginated.per_page,
        'total': paginated.total,
        'has_next': paginated.has_next,
        'has_prev': paginated.has_prev
    }

# User authentication endpoints
@api_bp.route('/auth/signup', methods=['POST'])
def signup():
    """User registration endpoint"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    required_fields = ['username', 'email', 'password', 'first_name', 'last_name', 'role']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Check if user already exists
    if User.query.filter_by(username=data['username'].lower()).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.query.filter_by(email=data['email'].lower()).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    try:
        user = User(
            username=data['username'].lower(),
            email=data['email'].lower(),
            first_name=data['first_name'],
            last_name=data['last_name'],
            role=data['role'],
            institution=data.get('institution'),
            year_level=data.get('year_level'),
            specialty=data.get('specialty')
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': 'User created successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.get_full_name()
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Signup error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """User login endpoint"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=data['email'].lower()).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account deactivated'}), 401
    
    # Update last seen
    user.last_seen = datetime.now(timezone.utc)
    db.session.commit()
    
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.get_full_name(),
            'role': user.role.value,
            'is_admin': user.is_admin
        }
    })

# User endpoints
@api_bp.route('/users/<int:user_id>')
@api_auth_required
def get_user(user_id):
    """Get user profile"""
    user = User.query.get_or_404(user_id)
    
    # Check privacy settings
    can_view = True
    if user.privacy_level.value == 'private' and current_user != user:
        can_view = False
    elif user.privacy_level.value == 'followers' and current_user != user:
        if not current_user.is_following(user):
            can_view = False
    
    if not can_view:
        return jsonify({'error': 'Private profile'}), 403
    
    return jsonify({
        'id': user.id,
        'username': user.username,
        'full_name': user.get_full_name(),
        'bio': user.bio,
        'role': user.role.value,
        'institution': user.institution,
        'specialty': user.specialty,
        'location': user.location,
        'created_at': user.created_at.isoformat(),
        'post_count': user.posts.count(),
        'follower_count': user.followers.count(),
        'following_count': user.followed.count(),
        'is_following': current_user.is_following(user) if current_user != user else False
    })

# Post endpoints
@api_bp.route('/posts', methods=['GET'])
@api_auth_required
def get_posts():
    """Get posts feed"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 50)
    
    posts = current_user.get_feed_posts().filter(Post.is_deleted == False)
    result = paginate_query(posts, page, per_page)
    
    # Format posts data
    posts_data = []
    for post in result['items']:
        posts_data.append({
            'id': post.id,
            'title': post.title,
            'content': post.content[:200] + '...' if len(post.content) > 200 else post.content,
            'post_type': post.post_type.value,
            'author': {
                'id': post.author.id,
                'username': post.author.username,
                'full_name': post.author.get_full_name()
            },
            'created_at': post.created_at.isoformat(),
            'views': post.views,
            'likes': post.likes,
            'comment_count': post.comments.filter_by(is_deleted=False).count(),
            'file_count': post.files.filter_by(is_deleted=False).count()
        })
    
    result['items'] = posts_data
    return jsonify(result)

@api_bp.route('/posts', methods=['POST'])
@api_auth_required
def create_post():
    """Create a new post"""
    data = request.get_json()
    
    if not data or not data.get('title') or not data.get('content'):
        return jsonify({'error': 'Title and content required'}), 400
    
    try:
        post = Post(
            title=data['title'],
            content=sanitize_html(data['content']),
            post_type=data.get('post_type', 'note'),
            user_id=current_user.id
        )
        
        db.session.add(post)
        db.session.commit()
        
        return jsonify({
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'post_type': post.post_type.value,
            'created_at': post.created_at.isoformat()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Post creation error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/posts/<int:post_id>')
@api_auth_required
def get_post(post_id):
    """Get a specific post"""
    post = Post.query.get_or_404(post_id)
    
    if post.is_deleted:
        return jsonify({'error': 'Post not found'}), 404
    
    # Increment view count
    post.views += 1
    db.session.commit()
    
    # Get comments
    comments = Comment.query.filter_by(post_id=post_id, is_deleted=False).order_by(Comment.created_at.asc()).all()
    comments_data = [{
        'id': comment.id,
        'content': comment.content,
        'author': {
            'id': comment.author.id,
            'username': comment.author.username,
            'full_name': comment.author.get_full_name()
        },
        'created_at': comment.created_at.isoformat()
    } for comment in comments]
    
    # Get files
    files = File.query.filter_by(post_id=post_id, is_deleted=False).all()
    files_data = [{
        'id': file.id,
        'filename': file.original_filename,
        'size': file.file_size,
        'mime_type': file.mime_type,
        'downloads': file.downloads
    } for file in files]
    
    return jsonify({
        'id': post.id,
        'title': post.title,
        'content': post.content,
        'post_type': post.post_type.value,
        'author': {
            'id': post.author.id,
            'username': post.author.username,
            'full_name': post.author.get_full_name()
        },
        'created_at': post.created_at.isoformat(),
        'updated_at': post.updated_at.isoformat(),
        'views': post.views,
        'likes': post.likes,
        'comments': comments_data,
        'files': files_data
    })

# Search endpoint
@api_bp.route('/search')
@api_auth_required
def search():
    """Search posts, users, and files"""
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 50)
    
    if not query or len(query) < 2:
        return jsonify({'error': 'Query must be at least 2 characters'}), 400
    
    results = {'posts': [], 'users': [], 'files': []}
    
    if search_type in ['all', 'posts']:
        posts_query = Post.query.filter(
            Post.is_deleted == False,
            db.or_(
                Post.title.contains(query),
                Post.content.contains(query)
            )
        ).order_by(Post.created_at.desc())
        
        posts_result = paginate_query(posts_query, page, per_page if search_type == 'posts' else 10)
        results['posts'] = [{
            'id': post.id,
            'title': post.title,
            'content': post.content[:200] + '...' if len(post.content) > 200 else post.content,
            'author': post.author.get_full_name(),
            'created_at': post.created_at.isoformat()
        } for post in posts_result['items']]
        
        if search_type == 'posts':
            results['pagination'] = {
                'page': posts_result['page'],
                'pages': posts_result['pages'],
                'total': posts_result['total']
            }
    
    if search_type in ['all', 'users']:
        users_query = User.query.filter(
            User.is_active == True,
            db.or_(
                User.username.contains(query),
                User.first_name.contains(query),
                User.last_name.contains(query)
            )
        ).order_by(User.created_at.desc())
        
        users_result = paginate_query(users_query, page, per_page if search_type == 'users' else 10)
        results['users'] = [{
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'role': user.role.value,
            'institution': user.institution
        } for user in users_result['items']]
        
        if search_type == 'users':
            results['pagination'] = {
                'page': users_result['page'],
                'pages': users_result['pages'],
                'total': users_result['total']
            }
    
    if search_type in ['all', 'files']:
        files_query = File.query.filter(
            File.is_deleted == False,
            File.original_filename.contains(query)
        ).order_by(File.created_at.desc())
        
        files_result = paginate_query(files_query, page, per_page if search_type == 'files' else 10)
        results['files'] = [{
            'id': file.id,
            'filename': file.original_filename,
            'size': file.file_size,
            'uploader': file.uploader.get_full_name(),
            'created_at': file.created_at.isoformat()
        } for file in files_result['items']]
        
        if search_type == 'files':
            results['pagination'] = {
                'page': files_result['page'],
                'pages': files_result['pages'],
                'total': files_result['total']
            }
    
    return jsonify(results)

# Message endpoints
@api_bp.route('/messages', methods=['POST'])
@api_auth_required
def send_message():
    """Send a message"""
    data = request.get_json()
    
    if not data or not data.get('recipient_id') or not data.get('content'):
        return jsonify({'error': 'Recipient and content required'}), 400
    
    recipient = User.query.get(data['recipient_id'])
    if not recipient:
        return jsonify({'error': 'Recipient not found'}), 404
    
    if recipient == current_user:
        return jsonify({'error': 'Cannot message yourself'}), 400
    
    try:
        message = Message(
            content=data['content'],
            sender_id=current_user.id,
            recipient_id=data['recipient_id']
        )
        
        db.session.add(message)
        db.session.commit()
        
        # Create notification
        create_notification(
            data['recipient_id'],
            f"New message from {current_user.get_full_name()}",
            "message",
            related_user_id=current_user.id
        )
        
        return jsonify({
            'id': message.id,
            'content': message.content,
            'created_at': message.created_at.isoformat()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Message send error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Admin endpoints
@api_bp.route('/admin/stats')
@api_auth_required
def admin_stats():
    """Get admin statistics"""
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    
    stats = {
        'total_users': User.query.filter_by(is_active=True).count(),
        'total_posts': Post.query.filter_by(is_deleted=False).count(),
        'total_files': File.query.filter_by(is_deleted=False).count(),
        'pending_flags': ContentFlag.query.filter_by(status='pending').count()
    }
    
    return jsonify(stats)

# Error handlers
@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@api_bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500
