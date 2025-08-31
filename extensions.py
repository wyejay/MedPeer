from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
mail = Mail()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()
