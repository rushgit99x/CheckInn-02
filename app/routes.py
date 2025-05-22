from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, Customer, TravelCompany, RoomType, Room, Reservation, TravelCompanyBooking, Billing, PaymentStatus
from app import db
from datetime import datetime
import json
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        check_in_date = request.form.get('check_in_date')
        check_out_date = request.form.get('check_out_date')
        number_of_occupants = request.form.get('number_of_occupants')
        
        logger.debug(f"Search form submitted: check_in_date={check_in_date}, check_out_date={check_out_date}, number_of_occupants={number_of_occupants}")
        
        try:
            check_in = datetime.strptime(check_in_date, '%Y-%m-%d').date()
            check_out = datetime.strptime(check_out_date, '%Y-%m-%d').date()
            occupants = int(number_of_occupants)
            if check_in >= check_out:
                flash('Check-out date must be after check-in date.', 'danger')
                return redirect(url_for('auth.index'))
            if occupants <= 0:
                flash('Number of occupants must be positive.', 'danger')
                return redirect(url_for('auth.index'))
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid search form data: {str(e)}")
            flash('Invalid search criteria. Please check your inputs.', 'danger')
            return redirect(url_for('auth.index'))
        
        # Redirect based on user type
        if current_user.is_authenticated and current_user.role == 'customer':
            if current_user.is_travel_company:
                return redirect(url_for('auth.bulk_reservation', check_in_date=check_in_date, check_out_date=check_out_date, number_of_occupants=number_of_occupants))
            else:
                return redirect(url_for('auth.book_room', check_in_date=check_in_date, check_out_date=check_out_date, number_of_occupants=number_of_occupants))
        else:
            flash('Please log in to book rooms.', 'warning')
            return redirect(url_for('auth.customer_login', next=url_for('auth.book_room', check_in_date=check_in_date, check_out_date=check_out_date, number_of_occupants=number_of_occupants)))
    
    room_types = RoomType.query.all()
    return render_template('index.html', room_types=room_types, current_user=current_user)

@auth_bp.route('/rooms', methods=['GET', 'POST'])
def rooms():
    # Base query for room types
    query = RoomType.query

    if request.method == 'POST':
        min_price = request.form.get('min_price')
        max_price = request.form.get('max_price')

        logger.debug(f"Filtering room types: min_price={min_price}, max_price={max_price}")

        # Apply filters
        if min_price:
            try:
                query = query.filter(RoomType.base_price >= float(min_price))
            except ValueError:
                flash('Invalid minimum price.', 'danger')
        if max_price:
            try:
                query = query.filter(RoomType.base_price <= float(max_price))
            except ValueError:
                flash('Invalid maximum price.', 'danger')

    room_types = query.all()
    if not room_types:
        flash('No room types match your criteria.', 'warning')

    return render_template('rooms.html', room_types=room_types)

@auth_bp.route('/customer/register', methods=['GET', 'POST'])
def customer_register():
    if current_user.is_authenticated:
        if current_user.role == 'customer':
            return redirect(url_for('auth.customer_dashboard' if not current_user.is_travel_company else 'auth.travel_company_dashboard'))
        else:
            return redirect(url_for('auth.staff_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        registration_type = request.form.get('registration_type')
        name = request.form.get('name')
        phone = request.form.get('phone')
        company_name = request.form.get('company_name')
        contact_email = request.form.get('contact_email')
        billing_details = request.form.get('billing_details')
        
        logger.debug(f"Registering user: username={username}, type={registration_type}, company_name={company_name}, contact_email={contact_email}")
        
        if not all([username, email, password, registration_type]):
            flash('All required fields must be filled.', 'danger')
            return redirect(url_for('auth.customer_register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('auth.customer_register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('auth.customer_register'))
        if registration_type == 'travel_company' and not (company_name and contact_email):
            flash('Company name and contact email are required for travel company registration.', 'danger')
            return redirect(url_for('auth.customer_register'))
        
        user = User(
            username=username,
            email=email,
            role='customer',
            is_travel_company=(registration_type == 'travel_company')
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        customer = Customer(
            user_id=user.user_id,
            name=name if registration_type != 'travel_company' else company_name,
            phone=phone
        )
        db.session.add(customer)
        
        if registration_type == 'travel_company':
            travel_company = TravelCompany(
                user_id=user.user_id,
                name=company_name,
                contact_email=contact_email,
                billing_details=billing_details
            )
            db.session.add(travel_company)
        
        try:
            db.session.commit()
            logger.info(f"User registered: user_id={user.user_id}, username={username}, is_travel_company={user.is_travel_company}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration failed for username={username}: {str(e)}")
            flash(f'Registration failed: {str(e)}', 'danger')
            return redirect(url_for('auth.customer_register'))
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.customer_login'))
    
    return render_template('customer_register.html')

@auth_bp.route('/staff/register', methods=['GET', 'POST'])
def staff_register():
    if current_user.is_authenticated:
        if current_user.role in ['clerk', 'manager']:
            return redirect(url_for('auth.staff_dashboard'))
        else:
            return redirect(url_for('auth.customer_dashboard' if not current_user.is_travel_company else 'auth.travel_company_dashboard'))
    
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
            role=role
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.staff_login'))
    
    return render_template('staff_register.html')

@auth_bp.route('/customer/login', methods=['GET', 'POST'])
def customer_login():
    if current_user.is_authenticated:
        if current_user.role == 'customer':
            return redirect(url_for('auth.customer_dashboard' if not current_user.is_travel_company else 'auth.travel_company_dashboard'))
        else:
            flash('Please use the staff portal.', 'danger')
            return redirect(url_for('auth.staff_login'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if user.role != 'customer':
                flash('Please use the staff portal.', 'danger')
                return redirect(url_for('auth.staff_login'))
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('auth.travel_company_dashboard' if user.is_travel_company else 'auth.customer_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('customer_login.html')

@auth_bp.route('/staff/login', methods=['GET', 'POST'])
def staff_login():
    if current_user.is_authenticated:
        if current_user.role in ['clerk', 'manager']:
            return redirect(url_for('auth.staff_dashboard'))
        else:
            flash('Please use the customer portal.', 'danger')
            return redirect(url_for('auth.customer_login'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if user.role not in ['clerk', 'manager']:
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
    role = current_user.role
    logout_user()
    flash('You have been logged out.', 'success')
    if role == 'customer':
        return redirect(url_for('auth.customer_login'))
    else:
        return redirect(url_for('auth.staff_login'))

@auth_bp.route('/customer/dashboard')
@login_required
def customer_dashboard():
    if current_user.role != 'customer' or current_user.is_travel_company:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.travel_company_dashboard' if current_user.is_travel_company else 'auth.staff_login'))
    customer = Customer.query.filter_by(user_id=current_user.user_id).first()
    return render_template('customer_dashboard.html', user_type='Customer', customer=customer)

@auth_bp.route('/customer/book_room', methods=['GET', 'POST'])
@login_required
def book_room():
    if current_user.role != 'customer' or current_user.is_travel_company:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.travel_company_dashboard' if current_user.is_travel_company else 'auth.staff_login'))
    
    customer = Customer.query.filter_by(user_id=current_user.user_id).first()
    if not customer:
        flash('Customer profile not found.', 'danger')
        return redirect(url_for('auth.customer_dashboard'))
    
    if request.method == 'POST':
        room_id = request.form['room_id']
        check_in_date = datetime.strptime(request.form['check_in_date'], '%Y-%m-%d').date()
        check_out_date = datetime.strptime(request.form['check_out_date'], '%Y-%m-%d').date()
        number_of_occupants = int(request.form['number_of_occupants'])
        
        if check_in_date >= check_out_date:
            flash('Check-out date must be after check-in date.', 'danger')
            return redirect(url_for('auth.book_room'))
        if number_of_occupants <= 0:
            flash('Number of occupants must be positive.', 'danger')
            return redirect(url_for('auth.book_room'))
        
        room = Room.query.get(room_id)
        if not room or room.status != 'available':
            flash('Room is not available.', 'danger')
            return redirect(url_for('auth.book_room'))
        
        conflicting = Reservation.query.filter(
            Reservation.room_id == room_id,
            Reservation.status != 'cancelled',
            Reservation.check_in_date <= check_out_date,
            Reservation.check_out_date >= check_in_date
        ).first()
        if conflicting:
            flash('Room is not available for the selected dates.', 'danger')
            return redirect(url_for('auth.book_room'))
        
        reservation = Reservation(
            customer_id=customer.customer_id,
            room_id=room_id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status='pending',
            number_of_occupants=number_of_occupants
        )
        room.status = 'occupied'
        db.session.add(reservation)
        db.session.commit()
        
        flash('Reservation created successfully!', 'success')
        return redirect(url_for('auth.customer_reservations'))
    
    rooms = Room.query.filter_by(status='available').all()
    return render_template('book_room.html', rooms=rooms)

# @auth_bp.route('/customer/reservations')
# @login_required
# def customer_reservations():
#     if current_user.role != 'customer' or current_user.is_travel_company:
#         flash('Unauthorized access.', 'danger')
#         return redirect(url_for('auth.travel_company_dashboard' if current_user.is_travel_company else 'auth.staff_login'))
    
#     customer = Customer.query.filter_by(user_id=current_user.user_id).first()
#     reservations = Reservation.query.filter_by(customer_id=customer.customer_id).all()
#     return render_template('customer_reservations.html', reservations=reservations)

@auth_bp.route('/customer/reservations')
@login_required
def customer_reservations():
    if current_user.role != 'customer' or current_user.is_travel_company:
        flash('Access denied.', 'danger')
        return redirect(url_for('auth.index'))
    reservations = Reservation.query.filter_by(customer_id=current_user.user_id).all()
    return render_template('customer_reservations.html', reservations=reservations)


@auth_bp.route('/customer/cancel_reservation/<int:reservation_id>', methods=['POST'])
@login_required
def cancel_reservation(reservation_id):
    if current_user.role != 'customer' or current_user.is_travel_company:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.travel_company_dashboard' if current_user.is_travel_company else 'auth.staff_login'))
    
    customer = Customer.query.filter_by(user_id=current_user.user_id).first()
    reservation = Reservation.query.get(reservation_id)
    if not reservation or reservation.customer_id != customer.customer_id:
        flash('Invalid reservation.', 'danger')
        return redirect(url_for('auth.customer_reservations'))
    
    if reservation.status not in ['pending', 'confirmed']:
        flash('Cannot cancel this reservation.', 'danger')
        return redirect(url_for('auth.customer_reservations'))
    
    reservation.status = 'cancelled'
    reservation.room.status = 'available'
    db.session.commit()
    
    flash('Reservation cancelled successfully.', 'success')
    return redirect(url_for('auth.customer_reservations'))

@auth_bp.route('/customer/travel_company_dashboard')
@login_required
def travel_company_dashboard():
    if current_user.role != 'customer' or not current_user.is_travel_company:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.customer_dashboard' if current_user.role == 'customer' else 'auth.staff_login'))
    company = TravelCompany.query.filter_by(user_id=current_user.user_id).first()
    return render_template('travel_company_dashboard.html', company=company)

@auth_bp.route('/customer/travel_company/bulk_reservation', methods=['GET', 'POST'])
@login_required
def bulk_reservation():
    if current_user.role != 'customer' or not current_user.is_travel_company:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.customer_dashboard' if current_user.role == 'customer' else 'auth.staff_login'))
    
    company = TravelCompany.query.filter_by(user_id=current_user.user_id).first()
    customer = Customer.query.filter_by(user_id=current_user.user_id).first()
    if not company:
        logger.error(f"TravelCompany profile not found for user_id={current_user.user_id}")
        flash('Travel company profile not found.', 'danger')
        return redirect(url_for('auth.travel_company_dashboard'))
    if not customer:
        logger.error(f"Customer profile not found for user_id={current_user.user_id}")
        flash('Customer profile not found.', 'danger')
        return redirect(url_for('auth.travel_company_dashboard'))
    
    if request.method == 'POST':
        logger.debug(f"Received POST data: {request.form}")
        room_ids = request.form.getlist('room_ids')
        if not room_ids:
            logger.warning("No rooms selected")
            flash('Please select at least one room.', 'danger')
            return redirect(url_for('auth.bulk_reservation'))
        
        try:
            check_in_date = datetime.strptime(request.form['check_in_date'], '%Y-%m-%d').date()
            check_out_date = datetime.strptime(request.form['check_out_date'], '%Y-%m-%d').date()
            number_of_occupants = int(request.form['number_of_occupants'])
            discount_rate = float(request.form.get('discount_rate', 0))
        except (ValueError, KeyError) as e:
            logger.error(f"Invalid form data: {str(e)}")
            flash('Invalid form data. Please check your inputs.', 'danger')
            return redirect(url_for('auth.bulk_reservation'))
        
        if check_in_date >= check_out_date:
            logger.warning("Invalid dates: check_in_date >= check_out_date")
            flash('Check-out date must be after check-in date.', 'danger')
            return redirect(url_for('auth.bulk_reservation'))
        if number_of_occupants <= 0:
            logger.warning("Invalid number of occupants")
            flash('Number of occupants must be positive.', 'danger')
            return redirect(url_for('auth.bulk_reservation'))
        
        total_amount = 0
        reservation_ids = []
        for room_id in room_ids:
            logger.debug(f"Processing room_id={room_id}")
            try:
                room = Room.query.get(int(room_id))
            except ValueError:
                logger.error(f"Invalid room_id: {room_id}")
                flash(f'Invalid room ID: {room_id}.', 'danger')
                return redirect(url_for('auth.bulk_reservation'))
            
            if not room:
                logger.error(f"Room ID {room_id} does not exist")
                flash(f'Room ID {room_id} does not exist.', 'danger')
                return redirect(url_for('auth.bulk_reservation'))
            if room.status != 'available':
                logger.warning(f"Room {room.room_number} is not available")
                flash(f'Room {room.room_number} is not available.', 'danger')
                return redirect(url_for('auth.bulk_reservation'))
            
            conflicting = Reservation.query.filter(
                Reservation.room_id == room_id,
                Reservation.status != 'cancelled',
                Reservation.check_in_date <= check_out_date,
                Reservation.check_out_date >= check_in_date
            ).first()
            if conflicting:
                logger.warning(f"Room {room.room_number} has conflicting reservation")
                flash(f'Room {room.room_number} is not available for the selected dates.', 'danger')
                return redirect(url_for('auth.bulk_reservation'))
            
            reservation = Reservation(
                customer_id=customer.customer_id,
                room_id=room_id,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                status='pending',
                number_of_occupants=number_of_occupants
            )
            db.session.add(reservation)
            db.session.flush()
            reservation_ids.append(reservation.reservation_id)
            nights = (check_out_date - check_in_date).days
            total_amount += room.room_type.base_price * nights
        
        total_amount *= (1 - discount_rate / 100)
        
        booking = TravelCompanyBooking(
            company_id=company.company_id,
            reservation_ids=json.dumps(reservation_ids),
            total_amount=total_amount,
            discount_rate=discount_rate,
            status='pending'
        )
        db.session.add(booking)
        
        try:
            for room_id in room_ids:
                room = Room.query.get(int(room_id))
                room.status = 'occupied'
            db.session.commit()
            logger.info(f"Bulk reservation created: booking_id={booking.booking_id}, reservation_ids={reservation_ids}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database commit failed: {str(e)}")
            flash(f'Failed to create booking: {str(e)}', 'danger')
            return redirect(url_for('auth.bulk_reservation'))
        
        flash('Bulk reservation created successfully!', 'success')
        return redirect(url_for('auth.travel_company_bookings'))
    
    rooms = Room.query.filter_by(status='available').all()
    if not rooms:
        logger.warning("No available rooms found")
        flash('No rooms are currently available.', 'warning')
    return render_template('bulk_reservation.html', rooms=rooms)

@auth_bp.route('/customer/travel_company/bookings')
@login_required
def travel_company_bookings():
    if current_user.role != 'customer' or not current_user.is_travel_company:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.customer_dashboard' if current_user.role == 'customer' else 'auth.staff_login'))
    
    company = TravelCompany.query.filter_by(user_id=current_user.user_id).first()
    bookings = TravelCompanyBooking.query.filter_by(company_id=company.company_id).all()
    return render_template('travel_company_bookings.html', bookings=bookings)

@auth_bp.route('/staff/dashboard')
@login_required
def staff_dashboard():
    if current_user.role not in ['clerk', 'manager']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.customer_login'))
    return render_template('staff_dashboard.html', user_type=current_user.role.capitalize())

@auth_bp.route('/staff/check_in_out', methods=['GET', 'POST'])
@login_required
def check_in_out():
    if current_user.role != 'clerk':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.staff_dashboard'))
    
    if request.method == 'POST':
        reservation_id = request.form['reservation_id']
        action = request.form['action']
        
        reservation = Reservation.query.get(reservation_id)
        if not reservation:
            flash('Invalid reservation.', 'danger')
            return redirect(url_for('auth.check_in_out'))
        
        if action == 'check_in' and reservation.status == 'confirmed':
            reservation.status = 'checked_in'
        elif action == 'check_out' and reservation.status == 'checked_in':
            reservation.status = 'checked_out'
            reservation.room.status = 'available'
        else:
            flash('Invalid action or reservation status.', 'danger')
            return redirect(url_for('auth.check_in_out'))
        
        db.session.commit()
        flash(f'Reservation {action.replace("_", "-")} successful.', 'success')
        return redirect(url_for('auth.check_in_out'))
    
    reservations = Reservation.query.filter(
        Reservation.status.in_(['pending', 'confirmed', 'checked_in'])
    ).all()
    return render_template('check_in_out.html', reservations=reservations)

@auth_bp.route('/staff/reservations')
@login_required
def staff_reservations():
    if current_user.role != 'clerk':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.staff_dashboard'))
    
    reservations = Reservation.query.all()
    return render_template('staff_reservations.html', reservations=reservations)

@auth_bp.route('/staff/occupancy_report')
@login_required
def occupancy_report():
    if current_user.role != 'manager':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.staff_dashboard'))
    
    total_rooms = Room.query.count()
    occupied_rooms = Reservation.query.filter(
        Reservation.status.in_(['confirmed', 'checked_in']),
        Reservation.check_in_date <= datetime.utcnow().date(),
        Reservation.check_out_date >= datetime.utcnow().date()
    ).count()
    occupancy_rate = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0
    
    return render_template('occupancy_report.html', occupancy_rate=occupancy_rate)

@auth_bp.route('/staff/financial_summary')
@login_required
def financial_summary():
    if current_user.role != 'manager':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.staff_dashboard'))
    
    total_revenue = db.session.query(db.func.sum(Billing.amount)).filter(
        Billing.payment_status == PaymentStatus.PAID
    ).scalar() or 0
    
    return render_template('financial_summary.html', total_revenue=total_revenue)

@auth_bp.route('/staff/manage_rooms', methods=['GET', 'POST'])
@login_required
def manage_rooms():
    if current_user.role != 'manager':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.staff_dashboard'))
    
    if request.method == 'POST':
        # Check if this is a room addition form submission
        if 'room_number' in request.form:
            room_number = request.form['room_number']
            type_id = request.form['type_id']
            price_per_night = float(request.form.get('price_per_night', 0))
            weekly_rate = float(request.form.get('weekly_rate', 0)) or None
            monthly_rate = float(request.form.get('monthly_rate', 0)) or None
            
            if not room_number.strip():
                flash('Room number cannot be empty.', 'danger')
                return redirect(url_for('auth.manage_rooms'))
            if price_per_night <= 0:
                flash('Price per night must be positive.', 'danger')
                return redirect(url_for('auth.manage_rooms'))
            if Room.query.filter_by(room_number=room_number).first():
                flash('Room number already exists.', 'danger')
                return redirect(url_for('auth.manage_rooms'))
            
            room = Room(
                room_number=room_number,
                type_id=type_id,
                price_per_night=price_per_night,
                weekly_rate=weekly_rate,
                monthly_rate=monthly_rate,
                status='available'
            )
            db.session.add(room)
            db.session.commit()
            flash('Room added successfully.', 'success')
        
        # Check if this is a room type addition form submission
        if 'type_name' in request.form:
            type_name = request.form['type_name'].strip()
            description = request.form['description'].strip()
            base_price = request.form['base_price']
            image_url = request.form.get('image_url', '').strip()
            
            if not type_name:
                flash('Room type name cannot be empty.', 'danger')
                return redirect(url_for('auth.manage_rooms'))
            if not description:
                flash('Description cannot be empty.', 'danger')
                return redirect(url_for('auth.manage_rooms'))
            if len(type_name) > 50:
                flash('Room type name must be 50 characters or less.', 'danger')
                return redirect(url_for('auth.manage_rooms'))
            if RoomType.query.filter_by(type_name=type_name).first():
                flash('Room type already exists.', 'danger')
                return redirect(url_for('auth.manage_rooms'))
            
            try:
                base_price = float(base_price)
                if base_price <= 0:
                    flash('Base price must be positive.', 'danger')
                    return redirect(url_for('auth.manage_rooms'))
            except ValueError:
                flash('Invalid base price. Must be a number.', 'danger')
                return redirect(url_for('auth.manage_rooms'))
            
            new_type = RoomType(
                type_name=type_name,
                description=description,
                base_price=base_price,
                image_url=image_url if image_url else None
            )
            db.session.add(new_type)
            db.session.commit()
            flash('Room type added successfully.', 'success')
    
    room_types = RoomType.query.all()
    rooms = Room.query.all()
    return render_template('manage_rooms.html', room_types=room_types, rooms=rooms)

@auth_bp.route('/staff/delete_room_type/<int:type_id>', methods=['POST'])
@login_required
def delete_room_type(type_id):
    if current_user.role != 'manager':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.staff_dashboard'))
    
    room_type = RoomType.query.get_or_404(type_id)
    
    # Check if any rooms are associated with this room type
    if room_type.rooms:
        flash(f'Cannot delete room type "{room_type.type_name}" because it is associated with {len(room_type.rooms)} room(s).', 'danger')
        return redirect(url_for('auth.manage_rooms'))
    
    try:
        db.session.delete(room_type)
        db.session.commit()
        flash(f'Room type "{room_type.type_name}" deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to delete room type {type_id}: {str(e)}")
        flash('Failed to delete room type. Please try again.', 'danger')
    
    return redirect(url_for('auth.manage_rooms'))