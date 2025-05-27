import pytest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sheetsift import create_app, db

@pytest.fixture
def client():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'UPLOAD_FOLDER': 'tests/uploads',
        'RESULT_FOLDER': 'tests/results',
        'SECRET_KEY': 'test_secret'
    }, testing=True)

    with app.app_context():
        db.create_all()

    with app.test_client() as client:
        yield client