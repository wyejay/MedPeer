from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from models import Post, Comment, File, Tag, ContentFlag, db
from forms import PostForm, CommentForm, FlagContentForm
from utils import save_uploaded_file, sanitize_html, extract_hashtags, create_notification
import os

posts_bp = Blueprint('posts', __name__)

@posts_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_post():
    """Create a new post"""
    form = PostForm()
    
    if form.validate_on_submit():
        try:
            # Sanitize content
            content = sanitize_html(form.content.data)
            
            # Create post
            post = Post(
                title=form.title.data,
                content=content,
                post_type=form.post_type.data,
                user_id=current_user.id
            )
            
            db.session.add(post)
            db.session.flush()  # Get post ID
            
            # Handle file uploads
            files = request.files.getlist('files')
            for file in files:
                if file and file.filename:
                    file_info = save_uploaded_file(file, subfolder='posts')
                    if file_info:
                        db_file = File(
                            filename=file_info['filename'],
                            original_filename=file_info['original_filename'],
                            file_path=file_info['file_path'],
                            file_size=file_info['file_size'],
                            mime_type=file_info['mime_type'],
                            file_hash=file_info['file_hash'],
                            user_id=current_user.id,
                            post_id=post.id
                        )
                        db.session.add(db_file)
            
            # Handle tags
            if form.tags.data:
                tag_names = [tag.strip().lower() for tag in form.tags.data.split(',')]
                for tag_name in tag_names:
                    if tag_name:
                        tag = Tag.query.filter_by(name=tag_name).first()
                        if not tag:
                            tag = Tag(name=tag_name)
                            db.session.add(tag)
                        post.tags.append(tag)
            
            # Extract hashtags from content
            hashtags = extract_hashtags(content)
            for hashtag in hashtags:
                tag_name = hashtag[1:].lower()  # Remove # symbol
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                if tag not in post.tags:
                    post.tags.append(tag)
            
            db.session.commit()
            flash('Your post has been created!', 'success')
            return redirect(url_for('posts.view_post', id=post.id))
        
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating your post.', 'danger')
            current_app.logger.error(f"Post creation error: {e}")
    
    return render_template('posts/create.html', form=form)

@posts_bp.route('/<int:id>')
def view_post(id):
    """View a single post"""
    post = Post.query.get_or_404(id)
    
    if post.is_deleted:
        flash('This post has been deleted.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    # Increment view count
    post.views += 1
    db.session.commit()
    
    # Get comments
    comments = Comment.query.filter_by(post_id=id, is_deleted=False).order_by(Comment.created_at.asc()).all()
    
    # Comment form
    comment_form = CommentForm()
    flag_form = FlagContentForm()
    
    return render_template('post_detail.html', 
                         post=post, 
                         comments=comments, 
                         comment_form=comment_form,
                         flag_form=flag_form)

@posts_bp.route('/<int:id>/comment', methods=['POST'])
@login_required
def add_comment(id):
    """Add a comment to a post"""
    post = Post.query.get_or_404(id)
    form = CommentForm()
    
    if form.validate_on_submit():
        try:
            content = sanitize_html(form.content.data)
            
            comment = Comment(
                content=content,
                post_id=id,
                user_id=current_user.id
            )
            
            db.session.add(comment)
            db.session.commit()
            
            # Create notification for post author
            if post.user_id != current_user.id:
                create_notification(
                    post.user_id,
                    f"{current_user.get_full_name()} commented on your post",
                    "comment",
                    related_post_id=post.id,
                    related_user_id=current_user.id
                )
            
            flash('Your comment has been added!', 'success')
        
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while adding your comment.', 'danger')
            current_app.logger.error(f"Comment error: {e}")
    
    return redirect(url_for('posts.view_post', id=id))

@posts_bp.route('/<int:id>/like', methods=['POST'])
@login_required
def like_post(id):
    """Like/unlike a post (simplified version)"""
    post = Post.query.get_or_404(id)
    
    # Simplified like system - just increment counter
    post.likes += 1
    db.session.commit()
    
    return jsonify({'likes': post.likes})

@posts_bp.route('/<int:id>/flag', methods=['POST'])
@login_required
def flag_post(id):
    """Flag a post for moderation"""
    post = Post.query.get_or_404(id)
    form = FlagContentForm()
    
    if form.validate_on_submit():
        try:
            flag = ContentFlag(
                reason=form.reason.data,
                description=form.description.data,
                reporter_id=current_user.id,
                post_id=id
            )
            
            db.session.add(flag)
            post.is_flagged = True
            db.session.commit()
            
            flash('Thank you for reporting this content. Our moderation team will review it.', 'info')
        
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while reporting this content.', 'danger')
            current_app.logger.error(f"Flag error: {e}")
    
    return redirect(url_for('posts.view_post', id=id))

@posts_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(id):
    """Edit a post"""
    post = Post.query.get_or_404(id)
    
    if post.user_id != current_user.id and not current_user.is_admin:
        flash('You can only edit your own posts.', 'danger')
        return redirect(url_for('posts.view_post', id=id))
    
    form = PostForm(obj=post)
    
    if form.validate_on_submit():
        try:
            post.title = form.title.data
            post.content = sanitize_html(form.content.data)
            post.post_type = form.post_type.data
            
            # Update timestamp
            from datetime import datetime, timezone
            post.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            flash('Your post has been updated!', 'success')
            return redirect(url_for('posts.view_post', id=id))
        
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your post.', 'danger')
            current_app.logger.error(f"Post update error: {e}")
    
    return render_template('posts/edit.html', form=form, post=post)

@posts_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_post(id):
    """Delete a post"""
    post = Post.query.get_or_404(id)
    
    if post.user_id != current_user.id and not current_user.is_admin:
        flash('You can only delete your own posts.', 'danger')
        return redirect(url_for('posts.view_post', id=id))
    
    try:
        # Soft delete
        post.is_deleted = True
        db.session.commit()
        
        flash('Your post has been deleted.', 'info')
        return redirect(url_for('main.dashboard'))
    
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting your post.', 'danger')
        current_app.logger.error(f"Post deletion error: {e}")
        return redirect(url_for('posts.view_post', id=id))

@posts_bp.route('/file/<int:file_id>')
@login_required
def download_file(file_id):
    """Download a file"""
    file = File.query.get_or_404(file_id)
    
    if file.is_deleted:
        flash('This file is no longer available.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Increment download count
        file.downloads += 1
        db.session.commit()
        
        return send_file(file.file_path, 
                        as_attachment=True, 
                        download_name=file.original_filename)
    
    except Exception as e:
        current_app.logger.error(f"File download error: {e}")
        flash('Error downloading file.', 'danger')
        return redirect(url_for('main.dashboard'))

@posts_bp.route('/tag/<tag_name>')
def posts_by_tag(tag_name):
    """View posts by tag"""
    tag = Tag.query.filter_by(name=tag_name.lower()).first_or_404()
    
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter(
        Post.tags.contains(tag),
        Post.is_deleted == False
    ).order_by(Post.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('posts/by_tag.html', tag=tag, posts=posts)

@posts_bp.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    """Delete a comment"""
    comment = Comment.query.get_or_404(comment_id)
    
    if comment.user_id != current_user.id and not current_user.is_admin:
        flash('You can only delete your own comments.', 'danger')
        return redirect(url_for('posts.view_post', id=comment.post_id))
    
    try:
        comment.is_deleted = True
        db.session.commit()
        
        flash('Your comment has been deleted.', 'info')
    
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting your comment.', 'danger')
        current_app.logger.error(f"Comment deletion error: {e}")
    
    return redirect(url_for('posts.view_post', id=comment.post_id))
