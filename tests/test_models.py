from sheetsift.models import User
from sheetsift import db, create_app

def test_user_creation():
    app = create_app({'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'}, testing=True)
    app.app_context().push()

    db.create_all()

    user = User(username="testuser", password="hashedpassword")
    db.session.add(user)
    db.session.commit()

    assert user.id is not None
    assert user.username == "testuser"

def test_user_repr():
    user = User(username="testuser", password="hashedpassword")
    assert repr(user) == '<User testuser>'

def test_load_user(app):
    from sheetsift import db
    from sheetsift.models import User, load_user
    with app.app_context():
        user = User(username="testuser_load", password="hashedpassword")
        db.session.add(user)
        db.session.commit()

        loaded_user = load_user(user.id)
        assert loaded_user is not None
        assert loaded_user.username == "testuser_load"

def test_admin_access_view_accessible(client, app):
    from sheetsift import db, bcrypt
    with app.app_context():
        hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
        user = User(username="Monty_Wizard_Python", password=hashed_pw)
        db.session.add(user)
        db.session.commit()

    client.post('/login', data={'username': 'Monty_Wizard_Python', 'password': 'testpass'})

    from sheetsift.models import AdminAccessView
    view = AdminAccessView(User, db.session)

    assert view.is_accessible() is True

def test_admin_access_view_inaccessible(client, app):
    from sheetsift import db, bcrypt
    with app.app_context():
        hashed_pw = bcrypt.generate_password_hash('testpass').decode('utf-8')
        user = User(username="nonadmin", password=hashed_pw)
        db.session.add(user)
        db.session.commit()

    client.post('/login', data={'username': 'nonadmin', 'password': 'testpass'})

    from sheetsift.models import AdminAccessView
    view = AdminAccessView(User, db.session)

    assert view.is_accessible() is False

def test_secure_user_admin_is_visible():
    from sheetsift.models import SecureUserAdmin
    from sheetsift import db
    view = SecureUserAdmin(User, db.session)

    assert view.is_visible() is True

def test_on_model_change_updates_password():
    from sheetsift.models import SecureUserAdmin, User
    from sheetsift import db, bcrypt
    from wtforms import Form, StringField

    user = User(username='testuser_on_model', password='oldpassword')
    db.session.add(user)
    db.session.commit()

    class DummyForm(Form):
        new_password = StringField()

    form = DummyForm()
    form.new_password.data = 'new_secure_password'

    view = SecureUserAdmin(User, db.session)
    view.on_model_change(form, user, is_created=False)

    assert bcrypt.check_password_hash(user.password, 'new_secure_password')

def test_inaccessible_callback_redirect(client, app):
    from sheetsift.models import AdminAccessView
    from urllib.parse import urlparse, parse_qs

    view = AdminAccessView(User, db.session)

    with app.test_request_context('/admin?param=test'):
        response = view.inaccessible_callback(name='test')

        assert response.status_code == 302

        parsed = urlparse(response.location)
        assert parsed.path == '/login'

        query_params = parse_qs(parsed.query)
        assert 'next' in query_params
        assert query_params['next'][0].startswith('http://')
        assert '/admin?param=test' in query_params['next'][0]