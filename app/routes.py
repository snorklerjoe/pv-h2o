from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import current_user, login_user, logout_user, login_required
from app import db
from app.models import User

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/index')
def index():
    return render_template('index.html', title='Home')

@bp.route('/dashboard')
def dashboard():
    # Placeholder for dashboard data
    return render_template('dashboard.html', title='Dashboard')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    # Login logic will go here
    return render_template('login.html', title='Sign In')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))
