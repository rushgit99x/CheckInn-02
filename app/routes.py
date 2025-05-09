from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, UserRole
from app import db, create_app

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    return render_template('index.html')

@auth_bp.route('/customer/register', methods=['GET', 'POST'])
def customer_register():
    app = create_app()
    with app.app_context():
        if current_user.is_authenticated:
            if current_user.role == UserRole.CUSTOMER:
                return redirect(url_for('auth.customer_dashboard'))
            else:
                return redirect(url_for('auth.staff_dashboard'))
        
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists.', 'danger')
                return redirect(url_for('auth.customer_register'))
            if User.query.filter_by(email=email).first():
                flash('Email already registered.', 'danger')
                return redirect(url_for('auth.customer_register'))
            
            user = User(
                username=username,
                email=email,
                role=UserRole.CUSTOMER
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.customer_login'))
        
        return render_template('customer_register.html')

@auth_bp.route('/staff/register', methods=['GET', 'POST'])
def staff_register():
    app = create_app()
    with app.app_context():
        if current_user.is_authenticated:
            if current_user.role in [UserRole.CLERK, UserRole.MANAGER]:
                return redirect(url_for('auth.staff_dashboard'))
            else:
                return redirect(url_for('auth.customer_dashboard'))
        
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            role = request.form['role']
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists.', 'danger')
                return redirect(url_for('auth.staff_register'))
            if User.query.filter_by(email=email).first():
                flash('Email already registered.', 'danger')
                return redirect(url_for('auth.staff_register'))
            if role not in ['clerk', 'manager']:
                flash('Invalid role selected.', 'danger')
                return redirect(url_for('auth.staff_register'))
            
            user = User(
                username=username,
                email=email,
                role=UserRole(role)
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.staff_login'))
        
        return render_template('staff_register.html')

@auth_bp.route('/customer/login', methods=['GET', 'POST'])
def customer_login():
    app = create_app()
    with app.app_context():
        if current_user.is_authenticated:
            if current_user.role == UserRole.CUSTOMER:
                return redirect(url_for('auth.customer_dashboard'))
            else:
                flash('Please use the staff portal.', 'danger')
                return redirect(url_for('auth.staff_login'))
        
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                if user.role != UserRole.CUSTOMER:
                    flash('Please use the staff portal.', 'danger')
                    return redirect(url_for('auth.staff_login'))
                login_user(user)
                flash('Login successful!', 'success')
                return redirect(url_for('auth.customer_dashboard'))
            else:
                flash('Invalid username or password.', 'danger')
        
        return render_template('customer_login.html')

@auth_bp.route('/staff/login', methods=['GET', 'POST'])
def staff_login():
    app = create_app()
    with app.app_context():
        if current_user.is_authenticated:
            if current_user.role in [UserRole.CLERK, UserRole.MANAGER]:
                return redirect(url_for('auth.staff_dashboard'))
            else:
                flash('Please use the customer portal.', 'danger')
                return redirect(url_for('auth.customer_login'))
        
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                if user.role not in [UserRole.CLERK, UserRole.MANAGER]:
                    flash('Please use the customer portal.', 'danger')
                    return redirect(url_for('auth.customer_login'))
                login_user(user)
                flash('Login successful!', 'success')
                return redirect(url_for('auth.staff_dashboard'))
            else:
                flash('Invalid username or password.', 'danger')
        
        return render_template('staff_login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    app = create_app()
    with app.app_context():
        role = current_user.role
        logout_user()
        flash('You have been logged out.', 'success')
        if role == UserRole.CUSTOMER:
            return redirect(url_for('auth.customer_login'))
        else:
            return redirect(url_for('auth.staff_login'))

@auth_bp.route('/customer/dashboard')
@login_required
def customer_dashboard():
    app = create_app()
    with app.app_context():
        if current_user.role != UserRole.CUSTOMER:
            flash('Unauthorized access.', 'danger')
            return redirect(url_for('auth.staff_login'))
        return render_template('customer_dashboard.html', user_type='Customer')

@auth_bp.route('/staff/dashboard')
@login_required
def staff_dashboard():
    app = create_app()
    with app.app_context():
        if current_user.role not in [UserRole.CLERK, UserRole.MANAGER]:
            flash('Unauthorized access.', 'danger')
            return redirect(url_for('auth.customer_login'))
        return render_template('staff_dashboard.html', user_type=current_user.role.value.capitalize())