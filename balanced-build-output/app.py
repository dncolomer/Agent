#!/usr/bin/env python3
import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask app
app = Flask(__name__)

# Load configuration from environment variables
app.config.from_object(os.environ['APP_SETTINGS'])

# Initialize database
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# Import models
from models import User, Content

# User loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    """Render the homepage"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if user exists and password is correct
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            # Log in user
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            # Show error message
            return render_template('login.html', error='Invalid email or password')

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle user signup"""
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if user already exists
        user = User.query.filter_by(email=email).first()
        if user:
            # Show error message
            return render_template('signup.html', error='Email already exists')

        # Create new user
        new_user = User(name=name, email=email, password=generate_password_hash(password, method='sha256'))
        db.session.add(new_user)
        db.session.commit()

        # Log in user
        login_user(new_user)
        return redirect(url_for('dashboard'))

    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Render the user dashboard"""
    # Get user's content
    content = Content.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', content=content)

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Handle content creation"""
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title')
        body = request.form.get('body')

        # Create new content
        new_content = Content(title=title, body=body, user_id=current_user.id)
        db.session.add(new_content)
        db.session.commit()

        return redirect(url_for('dashboard'))

    return render_template('create.html')

if __name__ == '__main__':
    app.run()