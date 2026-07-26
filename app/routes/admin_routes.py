from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from .. import db
from ..models import ParkingLot, ParkingSpot, User, Reservation

admin_bp = Blueprint('admin_bp', __name__)

@admin_bp.route('/secret-dashboard')
def admin_dashboard():
    search_query = request.args.get('search', '')
    if search_query:
        lots = ParkingLot.query.filter(
            ParkingLot.prime_location_name.contains(search_query) |
            ParkingLot.address.contains(search_query) |
            ParkingLot.pincode.contains(search_query)
        ).all()
    else:
        lots = ParkingLot.query.all()
    spots = ParkingSpot.query.all()
    users = User.query.all()
    reservations = Reservation.query.all()
    return render_template('admin_dashboard.html', lots=lots, spots=spots, users=users, reservations=reservations, active_tab='home', search_query=search_query)

@admin_bp.route('/admin/users')
def admin_users():
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@admin_bp.route('/admin/sales')
def admin_sales():
    from datetime import datetime, timedelta
    reservations = Reservation.query.all()
    
    # Calculate total sales of all time (completed reservations)
    total_sales_all_time = 0
    for r in reservations:
        if r.leaving_time and r.parking_time:
            hours = (r.leaving_time - r.parking_time).total_seconds() / 3600
            total_sales_all_time += r.cost_per_hour * hours
    
    # Calculate total sales of current month
    now = datetime.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
    total_sales_this_month = 0
    for r in reservations:
        if r.leaving_time and r.parking_time and start_of_month <= r.leaving_time <= end_of_month:
            hours = (r.leaving_time - r.parking_time).total_seconds() / 3600
            total_sales_this_month += r.cost_per_hour * hours
    
    # Get completed reservations for table
    completed_reservations = [r for r in reservations if r.leaving_time]
    
    # Prepare chart data for last 12 months
    chart_labels = []
    chart_sales_data = []
    chart_reservation_counts = []
    for i in range(11, -1, -1):
        month_start = (now - timedelta(days=30*i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        month_reservations = [r for r in reservations if r.leaving_time and r.parking_time and month_start <= r.leaving_time <= month_end]
        month_sales = sum(r.cost_per_hour * ((r.leaving_time - r.parking_time).total_seconds() / 3600) for r in month_reservations)
        chart_labels.append(month_start.strftime('%b %Y'))
        chart_sales_data.append(month_sales)
        chart_reservation_counts.append(len(month_reservations))
    
    return render_template('admin_sales.html', 
                         total_sales_all_time=round(total_sales_all_time, 2),
                         total_sales_this_month=round(total_sales_this_month, 2),
                         reservations=completed_reservations,
                         chart_labels=chart_labels,
                         chart_sales_data=chart_sales_data,
                         chart_reservation_counts=chart_reservation_counts)

@admin_bp.route('/admin/summary')
def admin_summary():
    lots = ParkingLot.query.all()
    summary = []
    for lot in lots:
        open_spots = sum(1 for s in lot.spots if s.status == 'A')
        reserved_spots = sum(1 for s in lot.spots if s.status == 'O')
        revenue = sum(r.cost_per_hour for s in lot.spots for r in s.reservations if r.leaving_time)
        summary.append({
            'lot_name': lot.prime_location_name,
            'total_spots': lot.max_spots,
            'open_spots': open_spots,
            'reserved_spots': reserved_spots,
            'revenue': revenue
        })
    return render_template('admin_summary.html', summary=summary)

# CRUD Operations for Parking Lots
@admin_bp.route('/admin/add_lot', methods=['POST'])
def add_lot():
    if request.method == 'POST':
        lot_name = request.form.get('lot_name')
        address = request.form.get('address')
        pincode = request.form.get('pincode')
        rate = request.form.get('rate')
        max_spots = request.form.get('max_spots')
        
        new_lot = ParkingLot(
            prime_location_name=lot_name,
            address=address,
            pincode=pincode,
            price_per_hour=float(rate),
            max_spots=int(max_spots)
        )
        db.session.add(new_lot)
        db.session.commit()
        flash('Parking lot added successfully!', 'success')
        return redirect(url_for('admin_bp.admin_dashboard'))

@admin_bp.route('/admin/edit_lot/<int:lot_id>')
def edit_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    return render_template('edit_lot.html', lot=lot)

@admin_bp.route('/admin/update_lot/<int:lot_id>', methods=['POST'])
def update_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    lot.prime_location_name = request.form.get('lot_name')
    lot.address = request.form.get('address')
    lot.pincode = request.form.get('pincode')
    lot.price_per_hour = float(request.form.get('rate'))
    lot.max_spots = int(request.form.get('max_spots'))
    db.session.commit()
    flash('Parking lot updated successfully!', 'success')
    return redirect(url_for('admin_bp.admin_dashboard'))

@admin_bp.route('/admin/delete_lot/<int:lot_id>', methods=['POST'])
def delete_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    db.session.delete(lot)
    db.session.commit()
    flash('Parking lot deleted successfully!', 'success')
    return redirect(url_for('admin_bp.admin_dashboard'))

# CRUD Operations for Parking Spots
@admin_bp.route('/admin/add_spot', methods=['POST'])
def add_spot():
    if request.method == 'POST':
        lot_id = request.form.get('lot_id')
        status = request.form.get('status')
        
        new_spot = ParkingSpot(
            lot_id=int(lot_id),
            status=status
        )
        db.session.add(new_spot)
        db.session.commit()
        flash('Parking spot added successfully!', 'success')
        return redirect(url_for('admin_bp.admin_dashboard'))

@admin_bp.route('/admin/update_spot/<int:spot_id>', methods=['POST'])
def update_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    status = request.form.get('status')
    spot.status = status
    db.session.commit()
    flash('Parking spot updated successfully!', 'success')
    return redirect(url_for('admin_bp.admin_dashboard'))

@admin_bp.route('/admin/delete_spot/<int:spot_id>', methods=['POST'])
def delete_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    db.session.delete(spot)
    db.session.commit()
    flash('Parking spot deleted successfully!', 'success')
    return redirect(url_for('admin_bp.admin_dashboard'))

@admin_bp.route('/login')
def admin_login():
    return render_template('admin_login.html')

@admin_bp.route('/logout')
def logout():
    # Clear admin session data
    session.clear()
    flash('Admin logged out successfully.', 'info')
    return redirect(url_for('main_bp.home'))



