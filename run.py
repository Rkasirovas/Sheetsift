import os
from sheetsift import create_app, db

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
config = {
    'UPLOAD_FOLDER': os.path.join(BASE_DIR, 'uploads'),
    'RESULT_FOLDER': os.path.join(BASE_DIR, 'results'),
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + os.path.join(BASE_DIR, 'app.db'),
    'SQLALCHEMY_TRACK_MODIFICATIONS': False
}

app = create_app(config)

if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists(os.path.join(BASE_DIR, 'app.db')):
            db.create_all()
            print("✅ Sukurtas app.db")
    app.run(debug=True)
