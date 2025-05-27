import os
import io
import tempfile
import pandas as pd
import pytest
from sheetsift import create_app, db
from flask import session
from unittest.mock import patch

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