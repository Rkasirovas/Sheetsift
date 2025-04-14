from flask import Blueprint, render_template, request, send_file, session, redirect, url_for, current_app
from .filters.seb import analyze_seb
from .filters.swedbank import analyze_swedbank
from flask_login import login_required
import os
from .utils import cleanup_temp_files

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def index():
    return render_template('index.html')

@main.route('/apie')
@login_required
def apie():
    return render_template('apie.html')

@main.route('/kontaktai')
@login_required
def kontaktai():
    return render_template('kontaktai.html')

@main.route('/sekmingai')
@login_required
def sekmingai():
    return render_template('sekmingai.html')

@main.route('/error')
@login_required
def klaida():
    return render_template('error.html')

@main.route('/sekmingai/atsisiusti')
@login_required
def atsisiusti():
    file_path = session.get('last_file')
    if file_path and os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return redirect(url_for('main.klaida'))

@main.route('/analyze', methods=['POST'])
@login_required
def analyze():
    bank = request.form.get('bank')
    if bank == 'seb':
        return analyze_seb()
    elif bank == 'swedbank':
        return analyze_swedbank()
    else:
        return render_template('error.html')

@main.route('/clean_up')
@login_required
def clean_up():
    upload_folder = current_app.config['UPLOAD_FOLDER']
    result_folder = current_app.config['RESULT_FOLDER']

    cleanup_temp_files(upload_folder, result_folder)
    session.pop('last_file', None)

    return redirect(url_for('main.index'))
