def test_home_redirect(client):
    response = client.get('/')
    assert response.status_code in (302, 200)

def test_error_page(client):
    response = client.get('/error')
    assert response.status_code in (200, 302)

def test_naudojimas_page(client):
    response = client.get('/naudojimas')
    assert response.status_code in (200, 302)

def test_kontaktai_page(client):
    response = client.get('/kontaktai')
    assert response.status_code in (200, 302)

def test_apie_redirect_authenticated(client, app):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=10, username='testuser10', password=hashed_pw)
    from sheetsift import db

    with app.app_context():
        db.session.add(user)
        db.session.commit()

    client.post('/login', data={'username': 'testuser10', 'password': 'testpass'})
    response = client.get('/apie', follow_redirects=False)

    assert response.status_code == 302
    assert '/' in response.location

def test_apie_unauthenticated(client):
    response = client.get('/apie', follow_redirects=False)
    assert response.status_code == 200
    assert b'Apie' in response.data

def test_sekmingai_redirect(client, app):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=11, username='testuser11', password=hashed_pw)
    from sheetsift import db

    with app.app_context():
        db.session.add(user)
        db.session.commit()

    client.post('/login', data={'username': 'testuser11', 'password': 'testpass'})
    response = client.get('/sekmingai', follow_redirects=False)

    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'sėkmingai' in html.lower()
    assert 'atsisiųsti failą' in html.lower()

import os

def test_sekmingai_atsisiusti_authenticated(client, app):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=12, username='testuser12', password=hashed_pw)
    from sheetsift import db

    with app.app_context():
        db.session.add(user)
        db.session.commit()

    client.post('/login', data={'username': 'testuser12', 'password': 'testpass'})

    test_results_dir = os.path.abspath('tests/results')
    os.makedirs(test_results_dir, exist_ok=True)
    test_file_path = os.path.join(test_results_dir, 'dummy.xlsx')

    with open(test_file_path, 'wb') as f:
        f.write(b'Test file content')

    with client.session_transaction() as session:
        session['last_file'] = test_file_path

    response = client.get('/sekmingai/atsisiusti', follow_redirects=False)

    _ = response.get_data()
    response.close()

    assert response.status_code == 200
    assert 'attachment' in response.headers.get('Content-Disposition', '')

    os.remove(test_file_path)

def test_sekmingai_atsisiusti_unauthenticated(client):
    response = client.get('/sekmingai/atsisiusti', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.location

def test_sekmingai_atsisiusti_no_file_in_session(client, app):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=13, username='testuser13', password=hashed_pw)
    from sheetsift import db

    with app.app_context():
        db.session.add(user)
        db.session.commit()

    client.post('/login', data={'username': 'testuser13', 'password': 'testpass'})

    response = client.get('/sekmingai/atsisiusti', follow_redirects=False)

    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert '404' in html

def test_index_authenticated(client, app):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=14, username='testuser14', password=hashed_pw)
    from sheetsift import db

    with app.app_context():
        db.session.add(user)
        db.session.commit()

    client.post('/login', data={'username': 'testuser14', 'password': 'testpass'})
    response = client.get('/')
    assert response.status_code == 200
    assert b'index' in response.data

def test_naudojimas_authenticated(client, app):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=15, username='testuser15', password=hashed_pw)
    from sheetsift import db

    with app.app_context():
        db.session.add(user)
        db.session.commit()

    client.post('/login', data={'username': 'testuser15', 'password': 'testpass'})
    response = client.get('/naudojimas')
    assert response.status_code == 200
    assert b'naudojimas' in response.data

def test_kontaktai_authenticated(client, app):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=16, username='testuser16', password=hashed_pw)
    from sheetsift import db

    with app.app_context():
        db.session.add(user)
        db.session.commit()

    client.post('/login', data={'username': 'testuser16', 'password': 'testpass'})
    response = client.get('/kontaktai')
    assert response.status_code == 200
    assert b'kontaktai' in response.data

def test_kita_authenticated(client, app):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=17, username='testuser17', password=hashed_pw)
    from sheetsift import db

    with app.app_context():
        db.session.add(user)
        db.session.commit()

    client.post('/login', data={'username': 'testuser17', 'password': 'testpass'})
    response = client.get('/kita')
    assert response.status_code == 200
    assert b'kita' in response.data

def test_klaida_route(client, app):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=18, username='testuser18', password=hashed_pw)
    from sheetsift import db

    with app.app_context():
        db.session.add(user)
        db.session.commit()

    client.post('/login', data={'username': 'testuser18', 'password': 'testpass'})
    response = client.get('/error')
    assert response.status_code == 200
    assert b'klaida' in response.data or b'error' in response.data

def test_analyze_invalid_bank(client, app):
    from sheetsift.models import User
    from sheetsift import bcrypt
    hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
    user = User(id=14, username='testuser14', password=hashed_pw)
    from sheetsift import db

    with app.app_context():
        db.session.add(user)
        db.session.commit()

    client.post('/login', data={'username': 'testuser14', 'password': 'testpass'})

    response = client.post('/analyze', data={'bank': 'nonexistentbank'})
    assert response.status_code == 200
    assert b'error' in response.data or b'klaida' in response.data

