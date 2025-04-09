from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from .models import User
from . import db

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_pw = generate_password_hash(password)

        # Patikrinam ar toks naudotojas jau egzistuoja
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Vartotojo vardas jau egzistuoja.', 'danger')
            return redirect(url_for('auth.register'))

        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash('Registracija sėkminga. Galite prisijungti.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Sėkmingai prisijungėte!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Neteisingas prisijungimo vardas arba slaptažodis.', 'danger')

    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Atsijungėte.', 'info')
    return redirect(url_for('auth.login'))
