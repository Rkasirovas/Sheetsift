from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_admin import Admin

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
admin = Admin(
    name='Monty_Wizard_Python',
    url='/montywizardpython',
    template_mode='bootstrap4'
)

login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def page_not_found(e):
    return render_template('404.html'), 404

def create_app(config=None, testing=False):
    app = Flask(__name__)
    app.secret_key = 'secret_key*#'

    if config:
        app.config.update(config)

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    if not testing:
        admin.init_app(app)
        from .models import User, SecureUserAdmin
        admin.add_view(SecureUserAdmin(User, db.session))

    from .routes import main
    from .auth import auth

    if 'main' not in app.blueprints:
        app.register_blueprint(main)

    if 'auth' not in app.blueprints:
        app.register_blueprint(auth)

    app.register_error_handler(404, page_not_found)

    return app