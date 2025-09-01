import os
from flask import Flask, render_template
from extensions import db, login_manager
from routes import main, auth, posts, messages, notifications, admin
from flask_migrate import Migrate
from models import User

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devkey')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    # Configure Flask-Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    Migrate(app, db)

    # Register blueprints
    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(posts)
    app.register_blueprint(messages)
    app.register_blueprint(notifications)
    app.register_blueprint(admin)

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        import traceback
        app.logger.error(f"500 error: {error}")
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        db.session.rollback()  # Rollback any failed database transactions
        if app.debug:
            return f"<pre>{traceback.format_exc()}</pre>", 500
        return render_template('errors/500.html'), 500

    return app

app = create_app()

# ✅ Create all tables automatically if they don't exist
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
