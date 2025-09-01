import os
from app import create_app

# Create the Flask application
app = create_app(os.environ.get('FLASK_ENV', 'default'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
from app import create_app, db

app = create_app()

with app.app_context():
    db.create_all()
    print("✅ Tables created!")
