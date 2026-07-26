# app/routes/main_routes.py

from flask import Blueprint, render_template, redirect, url_for

main_bp = Blueprint('main_bp', __name__)

@main_bp.route('/')
def home():
    return render_template('home.html')

@main_bp.route('/about')
def about():
    return render_template('about.html')

@main_bp.route('/login')
def login():
    return render_template('login.html')

@main_bp.route('/register')
def register():
    return render_template('register.html')

@main_bp.route('/admin-login')
def admin_login():
    return render_template('admin_login.html')
