import os
import io
import tempfile
import pandas as pd
import numpy as np
import pytest
from sheetsift import create_app, db
from unittest.mock import patch
import time

@pytest.fixture
def client():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'UPLOAD_FOLDER': 'tests/uploads',
        'RESULT_FOLDER': 'tests/results'
    }, testing=True)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

    app.app_context().push()
    db.create_all()
    with app.test_client() as client:
        yield client

def upload_test_file(client, df):
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    df.to_excel(tmp_file.name, index=False)
    with open(tmp_file.name, 'rb') as f:
        data = {'file': (f, 'test.xlsx')}
        response = client.post('/analyze', data=data, content_type='multipart/form-data')
    return response

def test_analyze_swedbank(client):
    df = pd.DataFrame({
        'Data': ['2024-01-01'],
        'Gavėjas / Siuntėjas': ['Testas'],
        'Gavėjo / Siuntėjo sąskaitos nr.': ['LT123'],
        'Sąskaitos Nr.': ['LT999'],
        'Detalės': ['Mokėjimas'],
        'Operacijos tipas': ['įplaukos'],
        'Suma': [100.0]
    })
    response = upload_test_file(client, df)
    assert response.status_code in (302, 200)

def test_analyze_seb(client):
    df = pd.DataFrame({
        'Nurašymo / įskaitymo data': ['2024-01-01'],
        'Operacijos aprašymas': ['Mokėjimas'],
        'Suma sąskaitos valiuta': [150.0]
    })
    response = upload_test_file(client, df)
    assert response.status_code in (302, 200)

def test_analyze_siauliu(client):
    df = pd.DataFrame({
        'Sąskaitos Nr.': ['LT123'],
        'Data': ['2024-01-01'],
        'Mokėjimo paskirtis': ['Už paslaugas'],
        'Debetas': [0],
        'Kreditas': [100]
    })
    response = upload_test_file(client, df)
    assert response.status_code in (302, 200)

def test_analyze_paysera(client):
    df = pd.DataFrame({
        'Date': ['2024-01-01'],
        'Amount (EUR)': [200.0],
        'Payee': ['Testas'],
        'Details': ['Apmokėjimas']
    })
    response = upload_test_file(client, df)
    assert response.status_code in (302, 200)

def test_analyze_revolut(client):
    df = pd.DataFrame({
        'Completed Date': ['2024-01-01'],
        'Amount': [300.0],
        'Description': ['Mokėjimas'],
        'Reference': ['Test ref']
    })
    response = upload_test_file(client, df)
    assert response.status_code in (302, 200)

def test_analyze_luminor(client):
    df = pd.DataFrame({
        'Data': ['2024-01-01'],
        'Aprašymas': ['Apmokėjimas'],
        'Suma': [400.0],
        'Sąskaita': ['LT321']
    })
    response = upload_test_file(client, df)
    assert response.status_code in (302, 200)

def test_analyze_citadele(client):
    df = pd.DataFrame({
        'Operation date': ['2024-01-01'],
        'Description': ['Mokėjimas'],
        'Amount': [500.0],
        'Account': ['LT654']
    })
    response = upload_test_file(client, df)
    assert response.status_code in (302, 200)

def test_citadele_en_account_format(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=1, username='testuser', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser', 'password': 'testpass'})

    df = pd.DataFrame({
        'Date': ['2024-01-01'],
        'Account Nr': ['LT123'],
        'Correspondent': ['Jonas'],
        'Details': ['Paslauga'],
        'Credit in transaction currency': [100.0],
        'Debit in transaction currency': [0.0],
    })

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        tmp_path = tmp_file.name
    df.to_excel(tmp_path, index=False)

    with patch('sheetsift.filters.citadele.schedule_file_deletion') as mock_delete:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'testas.xlsx'), 'bank': 'citadele'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert response.status_code in (302, 200)

        with client.session_transaction() as sess:
            assert 'last_file' in sess
            assert sess['last_file'].endswith('.xlsx')
            assert os.path.exists(sess['last_file'])

        mock_delete.assert_called_once()

    os.remove(tmp_path)

def test_citadele_en_iban_format(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=2, username='testuser2', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser2', 'password': 'testpass'})

    df = pd.DataFrame({
        'IBAN': ['LT123456789012345678'],
        'OFS.DATE': [20240101],
        'OFS.CNP.NAME': ['Jonas'],
        'OFS.NARRATIVE': ['Paslauga'],
        'OFS.AMOUNT': [250.0],
        'SIGN': ['CR'],
    })

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    df.to_excel(tmp_file.name, index=False)

    with patch('sheetsift.filters.citadele.schedule_file_deletion') as mock_delete:
        with open(tmp_file.name, 'rb') as f:
            data = {'file': (f, 'testas.xlsx'), 'bank': 'citadele'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert response.status_code in (302, 200)

        with client.session_transaction() as sess:
            assert 'last_file' in sess
            assert sess['last_file'].endswith('.xlsx')
            assert os.path.exists(sess['last_file'])

        mock_delete.assert_called_once()

    tmp_file.close()
    os.remove(tmp_file.name)

def test_citadele_lt_format(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=3, username='testuser3', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser3', 'password': 'testpass'})

    df = pd.DataFrame({
        'Data': ['01.01.2024'],
        'Operacijos numeris ir paskirtis': ['LT123456789012345678 Pavedimas'],
        'DR': [100.0],
        'CR': [0.0],
    })

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    df.to_excel(tmp_file.name, index=False)

    with patch('sheetsift.filters.citadele.schedule_file_deletion') as mock_delete:
        with open(tmp_file.name, 'rb') as f:
            data = {'file': (f, 'testas.xlsx'), 'bank': 'citadele'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert response.status_code in (302, 200)

        with client.session_transaction() as sess:
            assert 'last_file' in sess
            assert sess['last_file'].endswith('.xlsx')
            assert os.path.exists(sess['last_file'])

        mock_delete.assert_called_once()

    tmp_file.close()
    os.remove(tmp_file.name)

def test_citadele_invalid_format_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=1, username='testuser', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser', 'password': 'testpass'})

    df = pd.DataFrame({'random_col1': [1], 'random_col2': [2]})

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    tmp_path = tmp_file.name
    tmp_file.close()

    df.to_excel(tmp_path, index=False)

    try:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'testas.xlsx'), 'bank': 'citadele'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        _ = response.get_data()

        assert response.status_code == 302
        assert '/error' in response.location or '/klaida' in response.location

    finally:
        time.sleep(0.1)
        os.remove(tmp_path)

def test_citadele_exception_handling(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=1, username='testuser', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser', 'password': 'testpass'})

    data = {'file': (io.BytesIO(b'not an excel file'), 'testas.xlsx'), 'bank': 'citadele'}
    response = client.post('/analyze', data=data, content_type='multipart/form-data')

    assert response.status_code == 302
    assert '/error' in response.location

def test_citadele_empty_file_raises(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=1, username='testuser', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser', 'password': 'testpass'})

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    tmp_path = tmp_file.name
    tmp_file.close()

    pd.DataFrame().to_excel(tmp_path, index=False)

    try:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'testas.xlsx'), 'bank': 'citadele'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        assert '/error' in response.location

    finally:
        time.sleep(0.1)
        os.remove(tmp_path)

def test_citadele_wrong_extension_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=1, username='testuser', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser', 'password': 'testpass'})

    data = {'file': (io.BytesIO(b'test content'), 'test.txt'), 'bank': 'citadele'}
    response = client.post('/analyze', data=data, content_type='multipart/form-data')

    assert response.status_code == 302
    assert '/error' in response.location

def test_citadele_no_file_uploaded_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=1, username='testuser', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser', 'password': 'testpass'})

    response = client.post('/analyze', data={'bank': 'citadele'}, content_type='multipart/form-data')

    assert response.status_code == 400

def test_citadele_partial_column_match_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=4, username='testuser4', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser4', 'password': 'testpass'})

    df = pd.DataFrame({
        'Account Nr': ['LT123'],
        'Something Else': ['Test'],
        'Different': ['Data'],
    })

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    tmp_path = tmp_file.name
    tmp_file.close()

    df.to_excel(tmp_path, index=False)

    try:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'testas.xlsx'), 'bank': 'citadele'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        assert '/error' in response.location

    finally:
        os.remove(tmp_path)

def test_citadele_read_excel_error_triggers_exception(client, monkeypatch):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=1, username='testuser', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser', 'password': 'testpass'})

    def fake_read_excel(*args, **kwargs):
        raise ValueError("Fake error")

    import pandas as pd
    monkeypatch.setattr(pd, "read_excel", fake_read_excel)

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    tmp_path = tmp_file.name
    tmp_file.close()

    with open(tmp_path, 'rb') as f:
        data = {'file': (f, 'testas.xlsx'), 'bank': 'citadele'}
        response = client.post('/analyze', data=data, content_type='multipart/form-data')

    assert response.status_code == 302
    assert '/error' in response.location

    os.remove(tmp_path)

def test_citadele_fix_date_exceptions(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    import gc

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=1, username='testuser', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser', 'password': 'testpass'})

    df = pd.DataFrame({
        'Data': ['Not a date'],
        'Operacijos numeris ir paskirtis': ['LT123456789012345678 Pavedimas'],
        'DR': [0.0],
        'CR': [0.0],
    })

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    tmp_path = tmp_file.name
    tmp_file.close()

    df.to_excel(tmp_path, index=False)

    try:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'testas.xlsx'), 'bank': 'citadele'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert response.status_code == 302 or response.status_code == 200
    finally:
        time.sleep(0.1)
        gc.collect()
        os.remove(tmp_path)

def test_citadele_fix_date_nan(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=1, username='testuser', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser', 'password': 'testpass'})

    df = pd.DataFrame({
        'Data': [np.nan],
        'Operacijos numeris ir paskirtis': ['LT123456789012345678 Pavedimas'],
        'DR': [0.0],
        'CR': [0.0],
    })

    fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)
    df.to_excel(tmp_path, index=False)

    try:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'testas.xlsx'), 'bank': 'citadele'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert response.status_code in (302, 200)

    finally:
        time.sleep(0.1)
        os.remove(tmp_path)

def test_citadele_fix_date_double_exception(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=1, username='testuser', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser', 'password': 'testpass'})

    df = pd.DataFrame({
        'Data': ['abc123'],
        'Operacijos numeris ir paskirtis': ['LT123456789012345678 Pavedimas'],
        'DR': [0.0],
        'CR': [0.0],
    })

    fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)
    df.to_excel(tmp_path, index=False)

    try:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'testas.xlsx'), 'bank': 'citadele'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert response.status_code in (302, 200)
    finally:
        os.remove(tmp_path)

def test_citadele_selection_none_triggers_redirect(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=5, username='testuser5', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser5', 'password': 'testpass'})

    df = pd.DataFrame({
        'RandomColumn1': [1],
        'RandomColumn2': [2]
    })

    fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)

    df.to_excel(tmp_path, index=False)

    try:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'testas.xlsx'), 'bank': 'citadele'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        assert '/error' in response.location or '/klaida' in response.location

    finally:
        os.remove(tmp_path)

def test_citadele_no_valid_columns_triggers_redirect(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=6, username='testuser6', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser6', 'password': 'testpass'})

    df = pd.DataFrame({
        'RandomColumn1': [1],
        'RandomColumn2': [2],
    })

    fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)

    df.to_excel(tmp_path, index=False)

    try:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'testas.xlsx'), 'bank': 'citadele'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        assert '/klaida' in response.location or '/error' in response.location
    finally:
        os.remove(tmp_path)

def test_citadele_else_branch_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=99, username='testuser99', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser99', 'password': 'testpass'})

    df = pd.DataFrame({
        'Completely random': ['value'],
        'Another column': [123]
    })

    fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)
    df.to_excel(tmp_path, index=False)

    try:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'testas.xlsx'), 'bank': 'citadele'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        assert '/klaida' in response.location or '/error' in response.location
    finally:
        os.remove(tmp_path)

def test_luminor_success(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=6, username='testuser6', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser6', 'password': 'testpass'})

    df = pd.DataFrame({
        'Operacijos data': ['2024-05-01', '2024-05-02'],
        'Mokėjimo paskirtis': ['Už paslaugas', 'Prekės'],
        'Mokėtojas /\nGavėjas': ['Jonas', 'Petras'],
        'Mokėtojo / Gavėjo sąskaitos numeris, paslaugų teikėjo pavadinimas ir kodas': ['LT123456789012345678', 'LT987654321098765432'],
        'Suma nac. valiuta (kreditas)': [100.0, 0.0],
        'Suma nac. valiuta (debetas)': [0.0, 50.0],
    })

    fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)
    df.to_excel(tmp_path, index=False)

    try:
        with patch('sheetsift.filters.luminor.schedule_file_deletion') as mock_delete:
            with open(tmp_path, 'rb') as f:
                data = {'file': (f, 'testas.xlsx'), 'bank': 'luminor'}
                response = client.post('/analyze', data=data, content_type='multipart/form-data')

            assert response.status_code == 302
            assert '/sekmingai' in response.location

    finally:
        os.remove(tmp_path)

def test_luminor_missing_columns_redirects_to_error(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=7, username='testuser7', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser7', 'password': 'testpass'})

    df = pd.DataFrame({
        'Operacijos data': ['2024-05-01'],
        'Mokėjimo paskirtis': ['Prekė'],
        'Mokėtojas /\nGavėjas': ['Jonas'],
        'Mokėtojo / Gavėjo sąskaitos numeris, paslaugų teikėjo pavadinimas ir kodas': ['LT123456789012345678'],
        'Suma nac. valiuta (debetas)': [0.0],
    })

    fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)
    df.to_excel(tmp_path, index=False)

    try:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'testas.xlsx'), 'bank': 'luminor'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        assert '/klaida' in response.location or '/error' in response.location

    finally:
        os.remove(tmp_path)

def test_luminor_exception_triggers_error(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    import io

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=7, username='testuser7', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser7', 'password': 'testpass'})

    bad_file = io.BytesIO(b'Not an excel content')
    data = {'file': (bad_file, 'testas.xlsx'), 'bank': 'luminor'}

    response = client.post('/analyze', data=data, content_type='multipart/form-data')

    assert response.status_code == 302
    assert '/error' in response.location or '/klaida' in response.location

def test_luminor_wrong_extension_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=8, username='testuser8', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser8', 'password': 'testpass'})

    data = {'file': (io.BytesIO(b'test content'), 'test.txt'), 'bank': 'luminor'}
    response = client.post('/analyze', data=data, content_type='multipart/form-data')

    assert response.status_code == 302
    assert '/error' in response.location or '/klaida' in response.location

def test_luminor_no_file_uploaded_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=9, username='testuser9', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser9', 'password': 'testpass'})

    response = client.post('/analyze', data={'bank': 'luminor'}, content_type='multipart/form-data')

    assert response.status_code in (302, 400)

def test_luminor_missing_columns_triggers_error(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=10, username='testuser10', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser10', 'password': 'testpass'})

    df = pd.DataFrame({'RandomColumn': [1]})

    fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)
    df.to_excel(tmp_path, index=False)

    try:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'testas.xlsx'), 'bank': 'luminor'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        assert '/error' in response.location or '/klaida' in response.location
    finally:
        os.remove(tmp_path)

def test_paysera_missing_columns_triggers_redirect(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=10, username='testuser10', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser10', 'password': 'testpass'})

    df = pd.DataFrame({
        'Random Column': [1],
        'Another Column': [2]
    })

    fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)
    df.to_excel(tmp_path, index=False)

    try:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'testas.xlsx'), 'bank': 'paysera'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        assert '/klaida' in response.location or '/error' in response.location

    finally:
        os.remove(tmp_path)

def test_paysera_invalid_credit_debit_value(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=11, username='testuser11', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser11', 'password': 'testpass'})

    df = pd.DataFrame({
        'Data ir laikas': ['2024-05-01'],
        'Kreditas / Debetas': ['X'],
        'Suma': [100.0],
        'Gavėjas / Mokėtojas': ['Jonas'],
        'Paskirtis': ['Prekės']
    })

    fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)
    df.to_excel(tmp_path, index=False)

    try:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'testas.xlsx'), 'bank': 'paysera'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        assert '/klaida' in response.location or '/error' in response.location

    finally:
        os.remove(tmp_path)

def test_paysera_read_excel_error_triggers_redirect(client, monkeypatch):
    from sheetsift.models import User
    from sheetsift import bcrypt
    import pandas as pd

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=12, username='testuser12', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser12', 'password': 'testpass'})

    def fake_read_excel(*args, **kwargs):
        raise ValueError("Test error")

    monkeypatch.setattr(pd, "read_excel", fake_read_excel)

    fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)

    with open(tmp_path, 'rb') as f:
        data = {'file': (f, 'testas.xlsx'), 'bank': 'paysera'}
        response = client.post('/analyze', data=data, content_type='multipart/form-data')

    assert response.status_code == 302
    assert '/klaida' in response.location or '/error' in response.location

    os.remove(tmp_path)

def test_paysera_wrong_extension_triggers_redirect(client):
    from sheetsift.models import User
    from sheetsift import bcrypt

    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=13, username='testuser13', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser13', 'password': 'testpass'})

    data = {'file': (io.BytesIO(b'some text content'), 'test.txt'), 'bank': 'paysera'}
    response = client.post('/analyze', data=data, content_type='multipart/form-data')

    assert response.status_code == 302
    assert '/klaida' in response.location or '/error' in response.location

def test_paysera_debit_only(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=11, username='testuser11', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser11', 'password': 'testpass'})

    df = pd.DataFrame({
        'Data ir laikas': ['2024-05-01'],
        'Gavėjas / Mokėtojas': ['Jonas'],
        'EVP / IBAN': ['LT123456789012345678'],
        'Suma ir valiuta': [100.0],
        'Paskirtis': ['Prekės'],
        'Kreditas / Debetas': ['D'],
    })

    fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)
    df.to_excel(tmp_path, index=False)

    try:
        with patch('sheetsift.filters.paysera.schedule_file_deletion') as mock_delete:
            with open(tmp_path, 'rb') as f:
                data = {'file': (f, 'testas.xlsx'), 'bank': 'paysera'}
                response = client.post('/analyze', data=data, content_type='multipart/form-data')

            assert response.status_code == 302
            assert '/sekmingai' in response.location
            with client.session_transaction() as sess:
                assert 'last_file' in sess
            mock_delete.assert_called_once()
    finally:
        os.remove(tmp_path)

def test_paysera_credit_only(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=12, username='testuser12', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser12', 'password': 'testpass'})

    df = pd.DataFrame({
        'Data ir laikas': ['2024-05-01'],
        'Gavėjas / Mokėtojas': ['Jonas'],
        'EVP / IBAN': ['LT123456789012345678'],
        'Suma ir valiuta': [200.0],
        'Paskirtis': ['Paslauga'],
        'Kreditas / Debetas': ['K'],
    })

    fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)
    df.to_excel(tmp_path, index=False)

    try:
        with patch('sheetsift.filters.paysera.schedule_file_deletion') as mock_delete:
            with open(tmp_path, 'rb') as f:
                data = {'file': (f, 'testas.xlsx'), 'bank': 'paysera'}
                response = client.post('/analyze', data=data, content_type='multipart/form-data')

            assert response.status_code == 302
            assert '/sekmingai' in response.location
            with client.session_transaction() as sess:
                assert 'last_file' in sess
            mock_delete.assert_called_once()
    finally:
        os.remove(tmp_path)

def test_paysera_invalid_date_triggers_exception(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=13, username='testuser13', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser13', 'password': 'testpass'})

    df = pd.DataFrame({
        'Data ir laikas': ['not a date'],
        'Gavėjas / Mokėtojas': ['Jonas'],
        'EVP / IBAN': ['LT123456789012345678'],
        'Suma ir valiuta': [200.0],
        'Paskirtis': ['Paslauga'],
        'Kreditas / Debetas': ['K'],
    })

    fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)
    df.to_excel(tmp_path, index=False)

    try:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'testas.xlsx'), 'bank': 'paysera'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert response.status_code in (302, 200)

    finally:
        os.remove(tmp_path)

def test_paysera_multi_years_pivot(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=14, username='testuser14', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser14', 'password': 'testpass'})

    df = pd.DataFrame({
        'Data ir laikas': ['2023-01-01', '2024-01-01'],
        'Gavėjas / Mokėtojas': ['Jonas', 'Jonas'],
        'EVP / IBAN': ['LT123', 'LT123'],
        'Suma ir valiuta': [100.0, 200.0],
        'Paskirtis': ['Pervedimas', 'Pervedimas'],
        'Kreditas / Debetas': ['K', 'K'],
    })

    fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)
    df.to_excel(tmp_path, index=False)

    try:
        with patch('sheetsift.filters.paysera.schedule_file_deletion') as mock_delete:
            with open(tmp_path, 'rb') as f:
                data = {'file': (f, 'testas.xlsx'), 'bank': 'paysera'}
                response = client.post('/analyze', data=data, content_type='multipart/form-data')

            assert response.status_code == 302
            assert '/sekmingai' in response.location
            mock_delete.assert_called_once()
    finally:
        os.remove(tmp_path)

def test_revolut_counterparty_format(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    from unittest.mock import patch
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=1, username='testuser', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser', 'password': 'testpass'})

    df = pd.DataFrame({
        'Started Date': ['2024-01-01'],
        'Counterparty Name': ['Jonas'],
        'Counterparty Account Nbr': ['LT123456789'],
        'Description': ['Apmokėjimas'],
        'Amount (base currency)': [100.0],
    })

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        tmp_path = tmp_file.name
    df.to_excel(tmp_path, index=False)

    try:
        with patch('sheetsift.filters.revolut.schedule_file_deletion') as mock_delete:
            with open(tmp_path, 'rb') as f:
                data = {'file': (f, 'testas.xlsx'), 'bank': 'revolut'}
                response = client.post('/analyze', data=data, content_type='multipart/form-data')

            assert response.status_code == 302
            assert '/sekmingai' in response.location

            with client.session_transaction() as sess:
                assert 'last_file' in sess
                assert sess['last_file'].endswith('.xlsx')

            mock_delete.assert_called_once()
    finally:
        os.remove(tmp_path)

def test_revolut_started_date_description_amount_format(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    from unittest.mock import patch
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=2, username='testuser2', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser2', 'password': 'testpass'})

    df = pd.DataFrame({
        'Started Date': ['2024-02-02'],
        'Description': ['Apmokėjimas už paslaugas'],
        'Amount': [200.0],
    })

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        tmp_path = tmp_file.name
    df.to_excel(tmp_path, index=False)

    try:
        with patch('sheetsift.filters.revolut.schedule_file_deletion') as mock_delete:
            with open(tmp_path, 'rb') as f:
                data = {'file': (f, 'testas.xlsx'), 'bank': 'revolut'}
                response = client.post('/analyze', data=data, content_type='multipart/form-data')

            assert response.status_code == 302
            assert '/sekmingai' in response.location

            with client.session_transaction() as sess:
                assert 'last_file' in sess
                assert sess['last_file'].endswith('.xlsx')

            mock_delete.assert_called_once()
    finally:
        os.remove(tmp_path)

def test_revolut_invalid_format_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=3, username='testuser3', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser3', 'password': 'testpass'})

    df = pd.DataFrame({
        'RandomColumn1': [1],
        'RandomColumn2': [2],
    })

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        tmp_path = tmp_file.name
    df.to_excel(tmp_path, index=False)

    try:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'testas.xlsx'), 'bank': 'revolut'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        assert '/error' in response.location or '/klaida' in response.location
    finally:
        os.remove(tmp_path)

def test_revolut_exception_handling(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=4, username='testuser4', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser4', 'password': 'testpass'})

    data = {'file': (io.BytesIO(b'not an excel file'), 'testas.xlsx'), 'bank': 'revolut'}

    response = client.post('/analyze', data=data, content_type='multipart/form-data')

    assert response.status_code == 302
    assert '/error' in response.location or '/klaida' in response.location

def test_revolut_wrong_extension_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=5, username='testuser5', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser5', 'password': 'testpass'})

    data = {'file': (io.BytesIO(b'Test content'), 'testas.txt'), 'bank': 'revolut'}
    response = client.post('/analyze', data=data, content_type='multipart/form-data')

    assert response.status_code == 302
    assert '/error' in response.location or '/klaida' in response.location

def test_revolut_no_file_uploaded_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=6, username='testuser6', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser6', 'password': 'testpass'})

    response = client.post('/analyze', data={'bank': 'revolut'}, content_type='multipart/form-data')

    assert response.status_code == 400

def test_citadele_invalid_format_triggers_selection_else(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=8, username='testuser8', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser8', 'password': 'testpass'})

    df = pd.DataFrame({
        'RandomColumn1': [1],
        'RandomColumn2': [2],
    })

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        tmp_path = tmp_file.name
    df.to_excel(tmp_path, index=False)

    try:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'testas.xlsx'), 'bank': 'citadele'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        assert '/klaida' in response.location or '/error' in response.location
    finally:
        os.remove(tmp_path)

def test_seb_old_format(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=1, username='testuser1', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser1', 'password': 'testpass'})

    df = pd.DataFrame({
        'Nurašymo / įskaitymo data': ['2024-01-01'],
        'Operacijos aprašymas': ['Mokėtojas: Jonas'],
        'Suma sąskaitos valiuta': ['100,00'],
    })

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        tmp_path = tmp_file.name
    df.to_excel(tmp_path, index=False)

    try:
        with patch('sheetsift.filters.seb.schedule_file_deletion') as mock_delete:
            with open(tmp_path, 'rb') as f:
                data = {'file': (f, 'testas_seb_old.xlsx'), 'bank': 'seb'}
                response = client.post('/analyze', data=data, content_type='multipart/form-data')

            assert response.status_code == 302
            assert '/sekmingai' in response.location

            mock_delete.assert_called_once()
    finally:
        os.remove(tmp_path)

def test_seb_new_format(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=2, username='testuser2', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser2', 'password': 'testpass'})

    df = pd.DataFrame({
        'DATA': ['2024-01-02'],
        'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS': ['Jonas'],
        'SĄSKAITA': ['LT987654321'],
        'MOKĖJIMO PASKIRTIS': ['Apmokėjimas'],
        'SĄSKAITOS NR': ['LT112233445566'],
        'DEBETAS/KREDITAS': ['C'],
        'SUMA': [250.0]
    })

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        tmp_path = tmp_file.name
    df.to_excel(tmp_path, index=False)

    try:
        with patch('sheetsift.filters.seb.schedule_file_deletion') as mock_delete:
            with open(tmp_path, 'rb') as f:
                data = {'file': (f, 'testas_seb_new.xlsx'), 'bank': 'seb'}
                response = client.post('/analyze', data=data, content_type='multipart/form-data')

            assert response.status_code == 302
            assert '/sekmingai' in response.location

            mock_delete.assert_called_once()
    finally:
        os.remove(tmp_path)

def test_seb_invalid_format_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=3, username='testuser3', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser3', 'password': 'testpass'})

    df = pd.DataFrame({
        'RandomColumn1': [1],
        'RandomColumn2': [2],
    })

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        tmp_path = tmp_file.name
    df.to_excel(tmp_path, index=False)

    try:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'testas_seb_invalid.xlsx'), 'bank': 'seb'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        assert '/klaida' in response.location or '/error' in response.location
    finally:
        os.remove(tmp_path)

def test_seb_corrupted_file_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=4, username='testuser4', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser4', 'password': 'testpass'})

    data = {'file': (io.BytesIO(b'ne excel turinys'), 'testas_seb.xlsx'), 'bank': 'seb'}
    response = client.post('/analyze', data=data, content_type='multipart/form-data')

    assert response.status_code == 302
    assert '/klaida' in response.location or '/error' in response.location

def test_seb_wrong_extension_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=5, username='testuser5', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser5', 'password': 'testpass'})

    data = {'file': (io.BytesIO(b'ne excel turinys'), 'testas_seb.txt'), 'bank': 'seb'}
    response = client.post('/analyze', data=data, content_type='multipart/form-data')

    assert response.status_code == 302
    assert '/klaida' in response.location or '/error' in response.location

def test_seb_no_file_uploaded_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=6, username='testuser6', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'testuser6', 'password': 'testpass'})

    response = client.post('/analyze', data={'bank': 'seb'}, content_type='multipart/form-data')

    assert response.status_code == 400 or response.status_code == 302

def test_siauliu_success(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    from unittest.mock import patch
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=1, username='testuser1', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()
    client.post('/login', data={'username': 'testuser1', 'password': 'testpass'})

    df = pd.DataFrame({
        'Sąskaitos Nr.': ['LT123456789'],
        'Data': ['2024-01-01'],
        'Mokėjimo paskirtis': ['MOKĖTOJAS: Jonas GAVĖJAS: Petras LT987654321 Mokėjimo paskirtis: Testas'],
        'Debetas': [100.0],
        'Kreditas': [200.0]
    })

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        tmp_path = tmp_file.name
    df.to_excel(tmp_path, index=False)

    try:
        with patch('sheetsift.filters.siauliu.schedule_file_deletion') as mock_delete:
            with open(tmp_path, 'rb') as f:
                data = {'file': (f, 'siauliu_test.xlsx'), 'bank': 'siauliubankas'}
                response = client.post('/analyze', data=data, content_type='multipart/form-data',
                                       follow_redirects=False)

            assert response.status_code == 302
            assert '/sekmingai' in response.location

            assert response.status_code == 302
            assert '/sekmingai' in response.location

            with client.session_transaction() as sess:
                assert 'last_file' in sess
                assert sess['last_file'].endswith('.xlsx')

            mock_delete.assert_called_once()
    finally:
        os.remove(tmp_path)

def test_siauliu_missing_columns_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=2, username='testuser2', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()
    client.post('/login', data={'username': 'testuser2', 'password': 'testpass'})

    df = pd.DataFrame({
        'Sąskaitos Nr.': ['LT123456789'],
        'Data': ['2024-01-01'],
        'Mokėjimo paskirtis': ['Testas']
    })

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        tmp_path = tmp_file.name
    df.to_excel(tmp_path, index=False)

    try:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'siauliu_invalid.xlsx'), 'bank': 'siauliubankas'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data', follow_redirects=False)

        assert response.status_code == 302
        assert '/klaida' in response.location or '/error' in response.location
    finally:
        os.remove(tmp_path)

def test_siauliu_corrupted_file_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=3, username='testuser3', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()
    client.post('/login', data={'username': 'testuser3', 'password': 'testpass'})

    data = {'file': (io.BytesIO(b'not an excel file'), 'siauliu_corrupted.xlsx'), 'bank': 'siauliubankas'}
    response = client.post('/analyze', data=data, content_type='multipart/form-data', follow_redirects=False)

    assert response.status_code == 302
    assert '/klaida' in response.location or '/error' in response.location

def test_siauliu_wrong_extension_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=4, username='testuser4', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()
    client.post('/login', data={'username': 'testuser4', 'password': 'testpass'})

    data = {'file': (io.BytesIO(b'some text content'), 'siauliu_test.txt'), 'bank': 'siauliubankas'}
    response = client.post('/analyze', data=data, content_type='multipart/form-data', follow_redirects=False)

    assert response.status_code == 302
    assert '/klaida' in response.location or '/error' in response.location

def test_siauliu_no_file_uploaded_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=5, username='testuser5', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()
    client.post('/login', data={'username': 'testuser5', 'password': 'testpass'})

    response = client.post('/analyze', data={'bank': 'siauliubankas'}, content_type='multipart/form-data', follow_redirects=False)

    assert response.status_code == 302 or response.status_code == 400
    if response.status_code == 302:
        assert '/klaida' in response.location or '/error' in response.location

def test_swedbank_success(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    from unittest.mock import patch
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=1, username='testuser1', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()
    client.post('/login', data={'username': 'testuser1', 'password': 'testpass'})

    df = pd.DataFrame({
        'Data': ['2024-01-01'],
        'Gavėjas / Siuntėjas': ['Jonas'],
        'Gavėjo / Siuntėjo sąskaitos nr.': ['LT123456789'],
        'Sąskaitos Nr.': ['LT987654321'],
        'Detalės': ['Testinis pavedimas'],
        'Operacijos tipas': ['įplaukos'],
        'Suma': [100.0]
    })

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        tmp_path = tmp_file.name
    df.to_excel(tmp_path, index=False)

    try:
        with patch('sheetsift.filters.swedbank.schedule_file_deletion') as mock_delete:
            with open(tmp_path, 'rb') as f:
                data = {'file': (f, 'swedbank_test.xlsx'), 'bank': 'swedbank'}
                response = client.post('/analyze', data=data, content_type='multipart/form-data', follow_redirects=False)

            assert response.status_code == 302
            assert '/sekmingai' in response.location

            with client.session_transaction() as sess:
                assert 'last_file' in sess
                assert sess['last_file'].endswith('.xlsx')

            mock_delete.assert_called_once()
    finally:
        os.remove(tmp_path)

def test_swedbank_missing_columns_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=2, username='testuser2', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()
    client.post('/login', data={'username': 'testuser2', 'password': 'testpass'})

    df = pd.DataFrame({
        'Kitas Stulpelis': [1],
        'Dar Vienas': [2]
    })

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        tmp_path = tmp_file.name
    df.to_excel(tmp_path, index=False)

    try:
        with open(tmp_path, 'rb') as f:
            data = {'file': (f, 'swedbank_invalid.xlsx'), 'bank': 'swedbank'}
            response = client.post('/analyze', data=data, content_type='multipart/form-data', follow_redirects=False)

        assert response.status_code == 302
        assert '/klaida' in response.location or '/error' in response.location
    finally:
        os.remove(tmp_path)

def test_swedbank_corrupted_file_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=3, username='testuser3', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()
    client.post('/login', data={'username': 'testuser3', 'password': 'testpass'})

    data = {'file': (io.BytesIO(b'not an excel file'), 'swedbank_corrupted.xlsx'), 'bank': 'swedbank'}
    response = client.post('/analyze', data=data, content_type='multipart/form-data', follow_redirects=False)

    assert response.status_code == 302
    assert '/klaida' in response.location or '/error' in response.location

def test_swedbank_wrong_extension_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=4, username='testuser4', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()
    client.post('/login', data={'username': 'testuser4', 'password': 'testpass'})

    data = {'file': (io.BytesIO(b'some text content'), 'swedbank_test.txt'), 'bank': 'swedbank'}
    response = client.post('/analyze', data=data, content_type='multipart/form-data', follow_redirects=False)

    assert response.status_code == 302
    assert '/klaida' in response.location or '/error' in response.location

def test_swedbank_no_file_uploaded_redirects(client):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=5, username='testuser5', password=hashed_pw)
    from sheetsift import db
    db.session.add(user)
    db.session.commit()
    client.post('/login', data={'username': 'testuser5', 'password': 'testpass'})

    response = client.post('/analyze', data={'bank': 'swedbank'}, content_type='multipart/form-data', follow_redirects=False)

    assert response.status_code == 302 or response.status_code == 400
    if response.status_code == 302:
        assert '/klaida' in response.location or '/error' in response.location

