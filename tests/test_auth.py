from sheetsift import create_app, db, bcrypt
import pytest
from sheetsift.models import User

@pytest.fixture
def client():
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'}, testing=True)
    app.app_context().push()
    db.create_all()
    with app.test_client() as client:
        yield client

def test_register_login_logout(client):
    response = client.post('/register', data={'username': 'testuser', 'password': 'testpass'})
    assert response.status_code == 302  # Redirect

    response = client.post('/login', data={'username': 'testuser', 'password': 'testpass'})
    assert response.status_code == 302

    response = client.get('/logout')
    assert response.status_code == 302

def test_register_get_page(client):
    response = client.get('/register')
    assert response.status_code == 200
    assert "Registracija" in response.get_data(as_text=True) or "username" in response.get_data(as_text=True)

def test_register_existing_user(client):
    client.post('/register', data={'username': 'testuser', 'password': 'testpass'})

    response = client.post('/register', data={'username': 'testuser', 'password': 'testpass'})

    assert response.status_code == 200
    assert "Toks vardas jau naudojamas" in response.get_data(as_text=True)

def test_login_wrong_password(client):
    client.post('/register', data={'username': 'testuser', 'password': 'testpass'})

    response = client.post('/login', data={'username': 'testuser', 'password': 'netikslus'})

    assert response.status_code == 200
    assert "Neteisingas vardas ar slaptažodis" in response.get_data(as_text=True)

def test_login_get_page(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert "Prisijungimas" in response.get_data(as_text=True) or "username" in response.get_data(as_text=True)

def test_register_redirects_authenticated_user(client):
    hashed_pw = bcrypt.generate_password_hash('pass').decode('utf-8')
    user = User(username='user1', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'user1', 'password': 'pass'})
    response = client.get('/register', follow_redirects=False)
    assert response.status_code == 302
    assert response.location == '/'

def test_login_redirects_authenticated_user(client):
    hashed_pw = bcrypt.generate_password_hash('pass').decode('utf-8')
    user = User(username='user2', password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    client.post('/login', data={'username': 'user2', 'password': 'pass'})
    response = client.get('/login', follow_redirects=False)
    assert response.status_code == 302
    assert response.location == '/'