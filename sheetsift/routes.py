from flask import Blueprint, render_template, request, send_file, session, redirect, url_for
from .filters.seb import analyze_seb
from .filters.swedbank import analyze_swedbank
from flask_login import login_required
import os

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def index():
    return render_template('index.html')

@main.route('/apie')
def apie():
    return render_template('apie.html')

@main.route('/kontaktai')
def kontaktai():
    return render_template('kontaktai.html')

@main.route('/sekmingai')
def sekmingai():
    return render_template('sekmingai.html')

@main.route('/error')
def klaida():
    return render_template('error.html')

@main.route('/sekmingai/atsisiusti')
def atsisiusti():
    file_path = session.get('last_file')
    if file_path and os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return redirect(url_for('main.klaida'))

@main.route('/analyze', methods=['POST'])
def analyze():
    bank = request.form.get('bank')
    if bank == 'seb':
        return analyze_seb()
    elif bank == 'swedbank':
        return analyze_swedbank()
    else:
        return render_template('error.html')
