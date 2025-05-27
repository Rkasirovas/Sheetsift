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