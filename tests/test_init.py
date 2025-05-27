from sheetsift import page_not_found, create_app

def test_create_app_with_admin():
    app = create_app({'TESTING': False, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    assert app is not None

def test_404_handler(client):
    response = client.get('/neegzistuojantis_puslapis')
    assert response.status_code == 404
    assert "404" in response.get_data(as_text=True) or "nerastas" in response.get_data(as_text=True).lower()

def test_page_not_found_direct():
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'}, testing=True)
    with app.app_context():
        with app.test_request_context():
            response, status_code = page_not_found(None)
            assert status_code == 404
            assert "404" in response or "nerastas" in response.lower()