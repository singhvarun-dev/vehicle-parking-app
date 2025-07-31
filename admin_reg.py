from main import app, db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    if not User.query.filter_by(email='admin@gmail.com').first():
        admin = User(username='admin', email='admin@gmail.com',
                     password=generate_password_hash('admin'), is_admin=True)
        db.session.add(admin)
        db.session.commit()
        print("Admin user created.")
    else:
        print("Admin already exists.")
