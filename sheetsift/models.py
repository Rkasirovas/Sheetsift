from . import db, login_manager, bcrypt
from flask_login import UserMixin, current_user
from flask_admin.contrib.sqla import ModelView
from wtforms import PasswordField
from flask import redirect, request, url_for

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class AdminAccessView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.username == 'Monty_Wizard_Python'

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

    def is_visible(self):
        return False
