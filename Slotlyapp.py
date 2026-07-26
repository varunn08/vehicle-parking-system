from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    db.create_all()
    print("✅ Database created successfully.")

if __name__ == '__main__':
    app.run(debug=True)

# app/Slotlyapp.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from .app.models import User
from .app import db, bcrypt

user_bp = Blueprint('user', __name__)

@user_bp.route('/')
def home():
    return render_template('home.html')

@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        username = request.form['username']
        password = request.form['password']
        
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists', 'danger')
            return redirect(url_for('user.register'))

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(fullname=fullname, username=username, password=hashed_pw, role='user')
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('user.login'))

    return render_template('register.html')


@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role

            if user.role == 'admin':
                return redirect(url_for('admin.admin_dashboard'))
            else:
                return redirect(url_for('user.user_dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            return redirect(url_for('user.login'))

    return render_template('login.html')


@user_bp.route('/user/dashboard')
def user_dashboard():
    if session.get('role') != 'user':
        return redirect(url_for('user.login'))
    return render_template('user_dashboard.html')



from app.routes.admin_routes import admin_bp
from app.routes.user_routes import user_bp
from app.routes.main_routes import main_bp  # newly added

app.register_blueprint(admin_bp)
app.register_blueprint(user_bp, url_prefix="/user")  # if needed
app.register_blueprint(main_bp)  # no prefix for public routes


from app.routes.main_routes import main_bp
app.register_blueprint(main_bp)



# Slotlyapp.py

from flask import Flask
from app.routes.main_routes import main_bp
from app.routes.user_routes import user_bp
from app.routes.admin_routes import admin_bp

app = Flask(__name__)

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)

if __name__ == '__main__':
    app.run(debug=True)


@main_bp.route('/')
def home():
    return render_template('home.html')
