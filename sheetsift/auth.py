from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_user, logout_user, login_required
from .models import User
from . import db, bcrypt

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user:
            return render_template('register.html', message='Toks vardas jau naudojamas')

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('auth.login', success_message='Registracija sėkminga! Galite prisijungti'))

    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    success_message = request.args.get('success_message')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('main.index'))
        else:
            return render_template('login.html', message='Neteisingas vardas ar slaptažodis')

    return render_template('login.html', success_message=success_message)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
