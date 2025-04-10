from flask import Flask, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_bcrypt import Bcrypt
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from wtforms import PasswordField

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
admin = Admin(name='Admin', template_mode='bootstrap4')

login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app(config=None):
    app = Flask(__name__)
    app.secret_key = 'secret_key*#'

    if config:
        app.config.update(config)

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    admin.init_app(app)

    from .models import User

    class AdminAccessView(ModelView):
        def is_accessible(self):
            return current_user.is_authenticated and current_user.username == 'admin'

        def inaccessible_callback(self, name, **kwargs):
            return redirect(url_for('auth.login', next=request.url))

    class SecureUserAdmin(AdminAccessView):
        form_excluded_columns = ['password']

        def scaffold_form(self):
            form_class = super().scaffold_form()
            form_class.new_password = PasswordField('Naujas slaptažodis')
            return form_class

        def on_model_change(self, form, model, is_created):
            if form.new_password.data:
                model.password = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')

    admin.add_view(SecureUserAdmin(User, db.session))

    from .routes import main
    from .auth import auth

    app.register_blueprint(main)
    app.register_blueprint(auth)

    return app