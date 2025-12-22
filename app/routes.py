from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user, login_required
from app import db
from app.models import User
from app.forms import LoginForm
from app.dynconfig import DynConfig, ConfigCategory
from app.sunrise import light_window
from loguru import logger

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/index')
def index():
    return render_template('index.html', title='Home')

@bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', title='Dashboard')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            logger.warning(f"Failed login attempt for user: {form.username.data}")
            flash('Invalid username or password')
            return redirect(url_for('main.login'))
        login_user(user, remember=form.remember_me.data)
        logger.info(f"User logged in: {user.username}")
        next_page = request.args.get('next')
        if not next_page or url_for('main.index') not in next_page:
            next_page = url_for('main.index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@bp.route('/logout')
def logout():
    logger.info(f"User logged out: {current_user.username}")
    logout_user()
    return redirect(url_for('main.index'))

from app.config import Config

@bp.route('/settings')
@login_required
def settings():
    window = light_window()
    return render_template('settings.html', title='Settings', categories=[c.value for c in ConfigCategory], window=window, timezone=Config.TIMEZONE_NAME)

@bp.route('/sensors')
@login_required
def sensors():
    return render_template('sensor_readings.html', title='Sensor Readings')

@bp.route('/grapher')
@login_required
def grapher():
    return render_template('grapher.html', title='Grapher')

@bp.route('/logs')
@login_required
def logs():
    return render_template('logs.html', title='System Logs')

@bp.route('/watchdog')
@login_required
def watchdog():
    return render_template('watchdog.html', title='Watchdog Status')

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        username = request.form.get('username')
        name = request.form.get('name')
        password = request.form.get('password')
        
        if username:
            current_user.username = username
        if name:
            current_user.name = name
        if password:
            current_user.set_password(password)
            
        db.session.commit()
        flash('Profile updated successfully')
        return redirect(url_for('main.profile'))
        
    return render_template('profile.html', title='User Profile')

@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
def create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        name = request.form.get('name')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
        else:
            user = User(username=username, name=name)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('User created successfully')
            return redirect(url_for('main.create_user')) # Redirect back to create_user to see the list
            
    users = User.query.all()
    return render_template('create_user.html', title='Create User', users=users)

@bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        if user.id == current_user.id:
            flash('Cannot delete yourself')
        else:
            db.session.delete(user)
            db.session.commit()
            flash('User deleted successfully')
    else:
        flash('User not found')
    return redirect(url_for('main.create_user'))


