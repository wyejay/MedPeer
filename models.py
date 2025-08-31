from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
import enum

class UserRole(enum.Enum):
    STUDENT = "student"
    DOCTOR = "doctor"
    NURSE = "nurse"
    PHARMACIST = "pharmacist"
    LAB_SCIENTIST = "lab_scientist"
    ALLIED_HEALTH = "allied_health"
    ADMIN = "admin"

class PostType(enum.Enum):
    NOTE = "note"
    QUESTION = "question"
    ANNOUNCEMENT = "announcement"
    RESOURCE = "resource"

class PrivacyLevel(enum.Enum):
    PUBLIC = "public"
    FOLLOWERS = "followers"
    PRIVATE = "private"

# Association table for user followers
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

# Association table for post tags
post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    
    # Medical professional fields
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    institution = db.Column(db.String(200))
    year_level = db.Column(db.String(50))
    specialty = db.Column(db.String(100))
    
    # Profile fields
    bio = db.Column(db.Text)
    profile_picture = db.Column(db.String(200))
    location = db.Column(db.String(100))
    website = db.Column(db.String(200))
    linkedin = db.Column(db.String(200))
    
    # Privacy and verification
    privacy_level = db.Column(db.Enum(PrivacyLevel), default=PrivacyLevel.PUBLIC)
    email_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_seen = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    posts = db.relationship('Post', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy='dynamic')
    notifications = db.relationship('Notification', foreign_keys='Notification.user_id', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    files = db.relationship('File', backref='uploader', lazy='dynamic', cascade='all, delete-orphan')
    
    # Self-referential many-to-many for followers
    followed = db.relationship('User',
                              secondary=followers,
                              primaryjoin=(followers.c.follower_id == id),
                              secondaryjoin=(followers.c.followed_id == id),
                              backref=db.backref('followers', lazy='dynamic'),
                              lazy='dynamic')
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    def follow(self, user):
        """Follow a user"""
        if not self.is_following(user):
            self.followed.append(user)
    
    def unfollow(self, user):
        """Unfollow a user"""
        if self.is_following(user):
            self.followed.remove(user)
    
    def is_following(self, user):
        """Check if following a user"""
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0
    
    def get_posts(self):
        """Get user's posts"""
        return Post.query.filter_by(user_id=self.id).order_by(Post.created_at.desc())
    
    def get_feed_posts(self):
        """Get posts for user's feed (own posts + followed users)"""
        followed_posts = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)).filter(
            followers.c.follower_id == self.id)
        own_posts = Post.query.filter_by(user_id=self.id)
        return followed_posts.union(own_posts).order_by(Post.created_at.desc())
    
    def __repr__(self):
        return f'<User {self.username}>'

class Post(db.Model):
    __tablename__ = 'post'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    post_type = db.Column(db.Enum(PostType), nullable=False, default=PostType.NOTE)
    
    # User and timestamps
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Engagement
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    
    # Status
    is_flagged = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    
    # Relationships
    files = db.relationship('File', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    tags = db.relationship('Tag', secondary=post_tags, backref=db.backref('posts', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Post {self.title}>'

class Comment(db.Model):
    __tablename__ = 'comment'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    
    # References
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Status
    is_flagged = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    
    # Relationships
    author = db.relationship('User', backref='comments')
    
    def __repr__(self):
        return f'<Comment {self.id}>'

class File(db.Model):
    __tablename__ = 'file'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    file_hash = db.Column(db.String(64))  # SHA-256 hash for deduplication
    
    # References
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True, index=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=True, index=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    downloads = db.Column(db.Integer, default=0)
    
    # Status
    is_scanned = db.Column(db.Boolean, default=False)
    scan_result = db.Column(db.String(50))  # clean, infected, pending
    is_deleted = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<File {self.original_filename}>'

class Message(db.Model):
    __tablename__ = 'message'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    
    # References
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # Status
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    read_at = db.Column(db.DateTime)
    
    # Relationships
    files = db.relationship('File', backref='message', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Message {self.id}>'

class Notification(db.Model):
    __tablename__ = 'notification'
    
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(500), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # mention, reply, message, admin
    
    # References
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    related_post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True)
    related_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Status
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    def __repr__(self):
        return f'<Notification {self.id}>'

class Tag(db.Model):
    __tablename__ = 'tag'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<Tag {self.name}>'

class AdminAction(db.Model):
    __tablename__ = 'admin_action'
    
    id = db.Column(db.Integer, primary_key=True)
    action_type = db.Column(db.String(50), nullable=False)  # ban, suspend, delete_post, etc.
    description = db.Column(db.String(500))
    
    # References
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    target_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    target_post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Relationships
    admin = db.relationship('User', foreign_keys=[admin_id], backref='admin_actions')
    target_user = db.relationship('User', foreign_keys=[target_user_id])
    target_post = db.relationship('Post', foreign_keys=[target_post_id])
    
    def __repr__(self):
        return f'<AdminAction {self.action_type}>'

class ContentFlag(db.Model):
    __tablename__ = 'content_flag'
    
    id = db.Column(db.Integer, primary_key=True)
    reason = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # References
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # flagged user
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, reviewed, dismissed, acted
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Relationships
    reporter = db.relationship('User', foreign_keys=[reporter_id])
    flagged_post = db.relationship('Post', foreign_keys=[post_id])
    flagged_comment = db.relationship('Comment', foreign_keys=[comment_id])
    flagged_user = db.relationship('User', foreign_keys=[user_id])
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    
    def __repr__(self):
        return f'<ContentFlag {self.reason}>'

class SiteSettings(db.Model):
    __tablename__ = 'site_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.String(200))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<SiteSettings {self.key}>'
