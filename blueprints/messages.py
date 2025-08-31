from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_, and_
from models import User, Message, File, db
from forms import MessageForm
from utils import save_uploaded_file, create_notification, time_ago

messages_bp = Blueprint('messages', __name__)

@messages_bp.route('/')
@login_required
def inbox():
    """Message inbox"""
    page = request.args.get('page', 1, type=int)
    
    # Get conversations (latest message from each conversation)
    subquery = db.session.query(
        Message.sender_id,
        Message.recipient_id,
        db.func.max(Message.created_at).label('latest')
    ).filter(
        or_(
            Message.sender_id == current_user.id,
            Message.recipient_id == current_user.id
        )
    ).group_by(
        db.func.least(Message.sender_id, Message.recipient_id),
        db.func.greatest(Message.sender_id, Message.recipient_id)
    ).subquery()
    
    conversations = db.session.query(Message).join(
        subquery,
        and_(
            Message.created_at == subquery.c.latest,
            or_(
                and_(Message.sender_id == subquery.c.sender_id, 
                     Message.recipient_id == subquery.c.recipient_id),
                and_(Message.sender_id == subquery.c.recipient_id, 
                     Message.recipient_id == subquery.c.sender_id)
            )
        )
    ).order_by(Message.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('messages/inbox.html', conversations=conversations, time_ago=time_ago)

@messages_bp.route('/conversation/<int:user_id>')
@login_required
def conversation(user_id):
    """View conversation with a specific user"""
    user = User.query.get_or_404(user_id)
    
    if user == current_user:
        flash('You cannot message yourself!', 'warning')
        return redirect(url_for('messages.inbox'))
    
    page = request.args.get('page', 1, type=int)
    
    # Get messages between current user and specified user
    messages = Message.query.filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.recipient_id == user_id),
            and_(Message.sender_id == user_id, Message.recipient_id == current_user.id)
        )
    ).order_by(Message.created_at.asc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    # Mark messages from the other user as read
    unread_messages = Message.query.filter_by(
        sender_id=user_id,
        recipient_id=current_user.id,
        is_read=False
    ).all()
    
    for msg in unread_messages:
        msg.is_read = True
        from datetime import datetime, timezone
        msg.read_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    form = MessageForm()
    form.recipient_id.data = user_id
    
    return render_template('messages/conversation.html', 
                         user=user, 
                         messages=messages, 
                         form=form,
                         time_ago=time_ago)

@messages_bp.route('/send', methods=['POST'])
@login_required
def send_message():
    """Send a message"""
    form = MessageForm()
    
    if form.validate_on_submit():
        recipient_id = int(form.recipient_id.data)
        recipient = User.query.get_or_404(recipient_id)
        
        if recipient == current_user:
            flash('You cannot message yourself!', 'warning')
            return redirect(url_for('messages.inbox'))
        
        try:
            # Create message
            message = Message(
                content=form.content.data,
                sender_id=current_user.id,
                recipient_id=recipient_id
            )
            
            db.session.add(message)
            db.session.flush()  # Get message ID
            
            # Handle file attachments
            files = request.files.getlist('files')
            for file in files:
                if file and file.filename:
                    file_info = save_uploaded_file(file, subfolder='messages')
                    if file_info:
                        db_file = File(
                            filename=file_info['filename'],
                            original_filename=file_info['original_filename'],
                            file_path=file_info['file_path'],
                            file_size=file_info['file_size'],
                            mime_type=file_info['mime_type'],
                            file_hash=file_info['file_hash'],
                            user_id=current_user.id,
                            message_id=message.id
                        )
                        db.session.add(db_file)
            
            db.session.commit()
            
            # Create notification for recipient
            create_notification(
                recipient_id,
                f"New message from {current_user.get_full_name()}",
                "message",
                related_user_id=current_user.id
            )
            
            flash('Message sent!', 'success')
            return redirect(url_for('messages.conversation', user_id=recipient_id))
        
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while sending your message.', 'danger')
            current_app.logger.error(f"Message send error: {e}")
    
    return redirect(url_for('messages.inbox'))

@messages_bp.route('/compose/<int:user_id>')
@login_required
def compose(user_id):
    """Compose a new message to a specific user"""
    user = User.query.get_or_404(user_id)
    
    if user == current_user:
        flash('You cannot message yourself!', 'warning')
        return redirect(url_for('messages.inbox'))
    
    form = MessageForm()
    form.recipient_id.data = user_id
    
    return render_template('messages/compose.html', form=form, recipient=user)

@messages_bp.route('/search')
@login_required
def search_messages():
    """Search messages"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    
    messages = []
    if query:
        messages = Message.query.filter(
            and_(
                or_(
                    Message.sender_id == current_user.id,
                    Message.recipient_id == current_user.id
                ),
                Message.content.contains(query)
            )
        ).order_by(Message.created_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
    
    return render_template('messages/search.html', 
                         messages=messages, 
                         query=query, 
                         time_ago=time_ago)

@messages_bp.route('/unread-count')
@login_required
def unread_count():
    """Get count of unread messages (AJAX endpoint)"""
    count = Message.query.filter_by(
        recipient_id=current_user.id,
        is_read=False
    ).count()
    
    return jsonify({'count': count})

@messages_bp.route('/mark-read/<int:message_id>', methods=['POST'])
@login_required
def mark_read(message_id):
    """Mark a specific message as read"""
    message = Message.query.get_or_404(message_id)
    
    if message.recipient_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    message.is_read = True
    from datetime import datetime, timezone
    message.read_at = datetime.now(timezone.utc)
    db.session.commit()
    
    return jsonify({'success': True})

@messages_bp.route('/delete/<int:message_id>', methods=['POST'])
@login_required
def delete_message(message_id):
    """Delete a message (soft delete)"""
    message = Message.query.get_or_404(message_id)
    
    # Only sender or recipient can delete
    if message.sender_id != current_user.id and message.recipient_id != current_user.id:
        flash('You cannot delete this message.', 'danger')
        return redirect(url_for('messages.inbox'))
    
    try:
        # In a full implementation, you might want to track who deleted it
        # For now, we'll just remove it from database
        db.session.delete(message)
        db.session.commit()
        
        flash('Message deleted.', 'info')
    
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the message.', 'danger')
        current_app.logger.error(f"Message deletion error: {e}")
    
    return redirect(url_for('messages.inbox'))
