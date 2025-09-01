from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, TextAreaField, PasswordField, SelectField, BooleanField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError
from models import User, UserRole, PostType, PrivacyLevel

class LoginForm(FlaskForm):
    """User login form"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    """User registration form"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    
    role = SelectField('Role', choices=[
        (UserRole.STUDENT.value, 'Medical Student'),
        (UserRole.DOCTOR.value, 'Doctor'),
        (UserRole.NURSE.value, 'Nurse'),
        (UserRole.PHARMACIST.value, 'Pharmacist'),
        (UserRole.LAB_SCIENTIST.value, 'Laboratory Scientist'),
        (UserRole.ALLIED_HEALTH.value, 'Allied Health Professional')
    ], validators=[DataRequired()])
    
    institution = StringField('Institution', validators=[Optional(), Length(max=200)])
    year_level = StringField('Year/Level', validators=[Optional(), Length(max=50)])
    specialty = StringField('Specialty', validators=[Optional(), Length(max=100)])
    
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data.lower()).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data.lower()).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class ForgotPasswordForm(FlaskForm):
    """Forgot password form"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Reset Password')

class ResetPasswordForm(FlaskForm):
    """Reset password form"""
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

class EditProfileForm(FlaskForm):
    """Edit user profile form"""
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    bio = TextAreaField('Bio', validators=[Optional(), Length(max=500)])
    institution = StringField('Institution', validators=[Optional(), Length(max=200)])
    year_level = StringField('Year/Level', validators=[Optional(), Length(max=50)])
    specialty = StringField('Specialty', validators=[Optional(), Length(max=100)])
    location = StringField('Location', validators=[Optional(), Length(max=100)])
    website = StringField('Website', validators=[Optional(), Length(max=200)])
    linkedin = StringField('LinkedIn Profile', validators=[Optional(), Length(max=200)])
    
    privacy_level = SelectField('Privacy Level', choices=[
        (PrivacyLevel.PUBLIC.value, 'Public'),
        (PrivacyLevel.FOLLOWERS.value, 'Followers Only'),
        (PrivacyLevel.PRIVATE.value, 'Private')
    ], validators=[DataRequired()])
    
    profile_picture = FileField('Profile Picture', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    
    submit = SubmitField('Update Profile')

class PostForm(FlaskForm):
    """Create/edit post form"""
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Content', validators=[DataRequired()])
    post_type = SelectField('Type', choices=[
        (PostType.NOTE.value, 'Note'),
        (PostType.QUESTION.value, 'Question'),
        (PostType.ANNOUNCEMENT.value, 'Announcement'),
        (PostType.RESOURCE.value, 'Resource')
    ], validators=[DataRequired()])
    
    tags = StringField('Tags (comma-separated)', validators=[Optional()])
    files = FileField('Attachments', validators=[
        FileAllowed(['pdf', 'doc', 'docx', 'ppt', 'pptx', 'png', 'jpg', 'jpeg', 'mp4'], 
                   'Invalid file type!')
    ], render_kw={"multiple": True})
    
    submit = SubmitField('Post')

class CommentForm(FlaskForm):
    """Add comment form"""
    content = TextAreaField('Comment', validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField('Add Comment')

class MessageForm(FlaskForm):
    """Send message form"""
    recipient_id = HiddenField('Recipient', validators=[DataRequired()])
    content = TextAreaField('Message', validators=[DataRequired(), Length(max=1000)])
    files = FileField('Attachments', validators=[
        FileAllowed(['pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg'], 'Invalid file type!')
    ], render_kw={"multiple": True})
    submit = SubmitField('Send')

class SearchForm(FlaskForm):
    """Search form"""
    query = StringField('Search', validators=[DataRequired(), Length(min=2, max=100)])
    search_type = SelectField('Type', choices=[
        ('all', 'All'),
        ('posts', 'Posts'),
        ('users', 'Users'),
        ('files', 'Files')
    ], default='all')
    submit = SubmitField('Search')

class ContactForm(FlaskForm):
    """Contact form"""
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    subject = StringField('Subject', validators=[DataRequired(), Length(max=200)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(max=2000)])
    submit = SubmitField('Send Message')

class FlagContentForm(FlaskForm):
    """Flag content form"""
    reason = SelectField('Reason', choices=[
        ('spam', 'Spam'),
        ('inappropriate', 'Inappropriate Content'),
        ('harassment', 'Harassment'),
        ('misinformation', 'Misinformation'),
        ('copyright', 'Copyright Violation'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Report')

class AdminActionForm(FlaskForm):
    """Admin action form"""
    action_type = SelectField('Action', choices=[
        ('warn', 'Warn User'),
        ('suspend', 'Suspend User'),
        ('ban', 'Ban User'),
        ('delete_post', 'Delete Post'),
        ('delete_comment', 'Delete Comment')
    ], validators=[DataRequired()])
    description = TextAreaField('Reason', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Take Action')
