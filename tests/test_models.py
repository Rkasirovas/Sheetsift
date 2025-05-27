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
