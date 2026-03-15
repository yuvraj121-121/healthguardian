from flask import Flask
from extensions import db, login_manager
from dotenv import load_dotenv
import os
from models.user import User
from models.checkin import CheckIn
from models.report import Report
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'healthguardian-secret-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///healthguardian.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

from models.user import User
from models.checkin import CheckIn
from models.report import Report

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

from routes.auth import auth
from routes.main import main
from routes.checkin import checkin_bp

app.register_blueprint(auth)
app.register_blueprint(main)
app.register_blueprint(checkin_bp)

@app.route('/sw.js')
def service_worker():
    return app.send_static_file('sw.js'), 200, {
        'Content-Type': 'application/javascript',
        'Service-Worker-Allowed': '/'
    }

@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json'), 200, {
        'Content-Type': 'application/manifest+json'
    }
    
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("✅ Database ready!")
    app.run(debug=True)