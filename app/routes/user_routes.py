from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from .. import db, bcrypt
from ..models import User, Reservation, ParkingLot, ParkingSpot
from ..forms import RegistrationForm, LoginForm
from datetime import datetime

user_bp = Blueprint('user_bp', __name__)

@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            full_name=form.full_name.data,
            middle_name=form.middle_name.data,
            last_name=form.last_name.data,
            dob=form.dob.data,
            username=form.username.data,
            email=form.email.data,
            password=hashed_pw
        )
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please login!', 'success')
        return redirect(url_for('user_bp.login'))
    return render_template('register.html', form=form)

@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login successful.', 'success')
            return redirect(url_for('user_bp.dashboard'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('login.html', form=form)

@user_bp.route('/dashboard')
@login_required
def dashboard():
    # Get search query
    search_query = request.args.get('search', '')
    
    # Get parking lots with search filter
    if search_query:
        lots = ParkingLot.query.filter(
            ParkingLot.prime_location_name.contains(search_query) |
            ParkingLot.address.contains(search_query) |
            ParkingLot.pincode.contains(search_query)
        ).all()
    else:
        lots = ParkingLot.query.all()
    
    # Calculate available spots for each lot
    available_spots = {}
    for lot in lots:
        available_spots[lot.id] = sum(1 for spot in lot.spots if spot.status == 'A')
    
    # Get active reservations (not released yet)
    from datetime import datetime
    now = datetime.now()
    active_reservations = Reservation.query.filter(
        Reservation.user_id == current_user.id,
        Reservation.parking_time <= now,
        Reservation.leaving_time > now
    ).all()
    
    # Get all user's reservation history
    all_reservations = Reservation.query.filter_by(user_id=current_user.id).order_by(Reservation.parking_time.desc()).all()
    
    # Calculate analytics data
    analytics = calculate_user_analytics(current_user.id, all_reservations)
    
    return render_template('user_dashboard.html', 
                         lots=lots, 
                         available_spots=available_spots,
                         active_reservations=active_reservations,
                         history=all_reservations,
                         analytics=analytics)

def calculate_user_analytics(user_id, reservations):
    """Calculate comprehensive analytics for the user"""
    from datetime import datetime, timedelta
    
    now = datetime.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Basic stats
    total_reservations = len(reservations)
    completed_reservations = [r for r in reservations if r.leaving_time]
    active_reservations_count = len([r for r in reservations if not r.leaving_time])
    
    # Spending analytics (by duration)
    total_spent = 0
    monthly_spent = 0
    for r in completed_reservations:
        if r.leaving_time and r.parking_time:
            hours = (r.leaving_time - r.parking_time).total_seconds() / 3600
            cost = r.cost_per_hour * hours
            total_spent += cost
            if r.leaving_time >= start_of_month:
                monthly_spent += cost
    
    # Monthly spending for last 6 months
    monthly_spending = []
    monthly_labels = []
    for i in range(5, -1, -1):
        month_start = (now - timedelta(days=30*i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        month_reservations = [r for r in completed_reservations if r.leaving_time and r.parking_time and month_start <= r.leaving_time <= month_end]
        month_spending = sum(r.cost_per_hour * ((r.leaving_time - r.parking_time).total_seconds() / 3600) for r in month_reservations)
        monthly_spending.append(month_spending)
        monthly_labels.append(month_start.strftime('%b %Y'))
    
    # Usage patterns - most frequent days
    day_counts = {}
    for r in completed_reservations:
        day = r.parking_time.strftime('%A')
        day_counts[day] = day_counts.get(day, 0) + 1
    
    # Usage patterns - most frequent hours
    hour_counts = {}
    for r in completed_reservations:
        hour = r.parking_time.hour
        hour_counts[hour] = hour_counts.get(hour, 0) + 1
    
    # Favorite parking lots
    lot_counts = {}
    for r in completed_reservations:
        lot_name = r.spot.lot.prime_location_name
        lot_counts[lot_name] = lot_counts.get(lot_name, 0) + 1
    
    # Average parking duration
    durations = []
    for r in completed_reservations:
        if r.leaving_time and r.parking_time:
            duration = (r.leaving_time - r.parking_time).total_seconds() / 3600  # hours
            durations.append(duration)
    
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    return {
        'total_reservations': total_reservations,
        'completed_reservations': len(completed_reservations),
        'active_reservations': active_reservations_count,
        'total_spent': round(total_spent, 2),
        'monthly_spent': round(monthly_spent, 2),
        'monthly_spending': [round(x, 2) for x in monthly_spending],
        'monthly_labels': monthly_labels,
        'day_counts': day_counts,
        'hour_counts': hour_counts,
        'lot_counts': lot_counts,
        'avg_duration': round(avg_duration, 1),
        'top_lots': sorted(lot_counts.items(), key=lambda x: x[1], reverse=True)[:5],
        'top_days': sorted(day_counts.items(), key=lambda x: x[1], reverse=True),
        'top_hours': sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:6]
    }

@user_bp.route('/book/<int:lot_id>', methods=['POST'])
@login_required
def book_spot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    # Find an available spot
    spot = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').first()
    if not spot:
        flash('No available spots in this lot.', 'danger')
        return redirect(url_for('user_bp.dashboard'))
    # Mark spot as occupied
    spot.status = 'O'
    # Create reservation
    reservation = Reservation(
        spot_id=spot.id,
        user_id=current_user.id,
        parking_time=datetime.now(),
        cost_per_hour=lot.price_per_hour
    )
    db.session.add(reservation)
    db.session.commit()
    flash(f'Successfully booked a spot in {lot.prime_location_name}!', 'success')
    return redirect(url_for('user_bp.dashboard'))

@user_bp.route('/release', methods=['POST'])
@login_required
def release_reservation():
    reservation_id = request.form.get('reservation_id')
    if reservation_id:
        from datetime import datetime
        now = datetime.now()
        reservation = Reservation.query.filter(
            Reservation.id == reservation_id,
            Reservation.user_id == current_user.id,
            Reservation.parking_time <= now,
            Reservation.leaving_time > now
        ).first()
    else:
        reservation = None
    if not reservation:
        flash('No active reservation to release.', 'warning')
        return redirect(url_for('user_bp.dashboard'))
    reservation.leaving_time = datetime.now()
    spot = ParkingSpot.query.get(reservation.spot_id)
    spot.status = 'A'
    db.session.commit()
    flash('Reservation released successfully.', 'success')
    return redirect(url_for('user_bp.dashboard'))

@user_bp.route('/release/confirm', methods=['GET', 'POST'])
@login_required
def release_confirm():
    reservation = Reservation.query.filter_by(user_id=current_user.id, leaving_time=None).first()
    if not reservation:
        flash('No active reservation to release.', 'warning')
        return redirect(url_for('user_bp.dashboard'))
    spot = ParkingSpot.query.get(reservation.spot_id)
    lot = ParkingLot.query.get(spot.lot_id)
    if request.method == 'POST':
        end_time_str = request.form.get('end_time')
        end_time = datetime.strptime(end_time_str, "%Y-%m-%dT%H:%M")
        reservation.leaving_time = end_time
        spot.status = 'A'
        db.session.commit()
        flash('Reservation released successfully.', 'success')
        return redirect(url_for('user_bp.dashboard'))
    return render_template('release_confirm.html', reservation=reservation, spot=spot, lot=lot)

@user_bp.route('/book/<int:lot_id>/confirm', methods=['GET', 'POST'])
@login_required
def book_confirm(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    if request.method == 'POST':
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M")
        end_time = datetime.strptime(end_time_str, "%Y-%m-%dT%H:%M")
        # Find an available spot
        spot = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').first()
        if not spot:
            flash('No available spots in this lot.', 'danger')
            return redirect(url_for('user_bp.dashboard'))
        spot.status = 'O'
        reservation = Reservation(
            spot_id=spot.id,
            user_id=current_user.id,
            parking_time=start_time,
            leaving_time=end_time,
            cost_per_hour=lot.price_per_hour
        )
        db.session.add(reservation)
        db.session.commit()
        flash(f'Successfully booked a spot in {lot.prime_location_name}!', 'success')
        return redirect(url_for('user_bp.dashboard'))
    return render_template('book_confirm.html', lot=lot)

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        # Get form data
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate current password if changing password
        if new_password:
            if not current_password:
                flash('Current password is required to change password.', 'error')
                return render_template('edit_profile.html', user=current_user)
            
            if not bcrypt.check_password_hash(current_user.password, current_password):
                flash('Current password is incorrect.', 'error')
                return render_template('edit_profile.html', user=current_user)
            
            if new_password != confirm_password:
                flash('New passwords do not match.', 'error')
                return render_template('edit_profile.html', user=current_user)
            
            if len(new_password) < 6:
                flash('New password must be at least 6 characters long.', 'error')
                return render_template('edit_profile.html', user=current_user)
        
        # Check if email is already taken by another user
        if email != current_user.email:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Email is already registered by another user.', 'error')
                return render_template('edit_profile.html', user=current_user)
        
        # Update user information
        current_user.full_name = full_name
        current_user.email = email
        
        # Update password if provided
        if new_password:
            current_user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        
        # Save changes
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user_bp.dashboard'))
    
    return render_template('edit_profile.html', user=current_user)

@user_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('user_bp.login'))

@user_bp.route('/extend/<int:reservation_id>', methods=['GET', 'POST'])
@login_required
def extend_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.user_id != current_user.id or not reservation.leaving_time:
        flash('Invalid reservation or permission denied.', 'danger')
        return redirect(url_for('user_bp.dashboard'))
    if request.method == 'POST':
        new_end_str = request.form.get('new_end_time')
        from datetime import datetime
        new_end = datetime.strptime(new_end_str, "%Y-%m-%dT%H:%M")
        if new_end <= reservation.leaving_time:
            flash('New end time must be after current end time.', 'danger')
            return render_template('extend_reservation.html', reservation=reservation)
        reservation.leaving_time = new_end
        db.session.commit()
        flash('Reservation extended successfully!', 'success')
        return redirect(url_for('user_bp.dashboard'))
    return render_template('extend_reservation.html', reservation=reservation)
