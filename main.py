import os
from app import create_app
from config import config

# Get environment configuration
config_name = os.environ.get('FLASK_ENV', 'development')

# Create the Flask application with proper config
app = create_app()

# Load configuration
app.config.from_object(config[config_name])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
