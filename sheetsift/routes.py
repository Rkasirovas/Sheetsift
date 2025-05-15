from flask import Blueprint, render_template, request, send_file, session, redirect, url_for, current_app
from .filters.seb import analyze_seb
from .filters.swedbank import analyze_swedbank
from .filters.luminor import analyze_luminor
from .filters.citadele import analyze_citadele
from .filters.paysera import analyze_paysera
from flask_login import login_required, current_user
import os
from .utils import cleanup_temp_files

main = Blueprint('main', __name__)

@main.route('/apie')
def apie():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    return render_template('apie.html')

@main.route('/')
@login_required
def index():
    return render_template('index.html')

@main.route('/naudojimas')
@login_required
def naudojimas():
    return render_template('naudojimas.html')

@main.route('/kontaktai')
@login_required
def kontaktai():
    return render_template('kontaktai.html')

@main.route('/kita')
@login_required
def kita():
    return render_template('kita.html')

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
    elif bank == 'luminor':
        return analyze_luminor()
    elif bank == 'citadele':
        return analyze_citadele()
    elif bank == 'paysera':
        return analyze_paysera()
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
