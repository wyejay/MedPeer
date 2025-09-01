import os
import hashlib
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app

def allowed_file(filename):
    """Check if a file is allowed based on its extension."""
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def generate_file_hash(file_data):
    """Generate a SHA-256 hash for the file content."""
    sha256 = hashlib.sha256()
    sha256.update(file_data)
    return sha256.hexdigest()

def save_file(file, upload_folder=None):
    """Save uploaded file to the server and return file info."""
    if upload_folder is None:
        upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
    
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    filename = secure_filename(file.filename)
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    
    file.seek(0)  # reset file pointer for hashing
    file_hash = generate_file_hash(file.read())
    
    return {
        "filename": filename,
        "file_path": file_path,
        "file_size": os.path.getsize(file_path),
        "mime_type": file.mimetype,
        "file_hash": file_hash,
        "uploaded_at": datetime.utcnow()
    }
