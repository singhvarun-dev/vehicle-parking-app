from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Mall, ParkingSpot, Reservation, Feedback
from datetime import datetime
import math, qrcode, io, base64

app = Flask(__name__)
app.secret_key = '12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
with app.app_context():
    db.create_all()

def calculate_cost(start, end, rate):
    seconds = (end - start).total_seconds()
    hours = int(seconds // 3600) + (1 if seconds % 3600 > 0 else 0)
    return rate * max(1, hours)

def is_logged_in():
    return 'user_id' in session

def is_admin():
    return session.get('is_admin', False)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        pw = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, pw):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            flash('Logged in', 'success')
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        flash('Invalid credentials', 'danger')
        return render_template('auth/login.html')
    return render_template('auth/login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        pw = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already taken', 'danger')
            return render_template('auth/register.html')
        hashed_pw = generate_password_hash(pw)
        newuser = User(username=username, email=email, password=hashed_pw)
        db.session.add(newuser)
        db.session.commit()
        flash('Registered successfully', 'success')
        return redirect(url_for('login'))
    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'info')
    return redirect(url_for('home'))

# Admin Routes ------------------------------------------------------------------

@app.route('/admin')
def admin_dashboard():
    if not is_admin():
        flash('Admin only!', 'danger')
        return redirect(url_for('login'))

    filter_loc = request.args.get('location', '').lower()
    sort_by = request.args.get('sort', 'name')
    query = Mall.query
    if filter_loc:
        query = query.filter(Mall.location.ilike(f'%{filter_loc}%'))
    lots = query.all()

    if sort_by == 'price':
        lots.sort(key=lambda l: l.price)
    elif sort_by == 'spots_available':
        lots.sort(key=lambda l: sum(s.status=='Available' for s in l.spots), reverse=True)
    else:
        lots.sort(key=lambda l: l.name.lower())

    users = User.query.filter_by(is_admin=False).all()
    reservations = Reservation.query.order_by(Reservation.start_time.desc()).all()

    spot_num = request.args.get('spot_num', '').lower()
    for lot in lots:
        if spot_num:
            lot.filtered_spots = [s for s in lot.spots if spot_num in s.slot_number.lower()]
        else:
            lot.filtered_spots = lot.spots

    return render_template('admin.html', lots=lots, users=users, reservations=reservations)

@app.route('/add_lot', methods=['POST'])
def add_lot():
    if not is_admin():
        return redirect(url_for('login'))
    name = request.form['name']
    location = request.form['location']
    price = float(request.form['price'])
    address = request.form['address']
    pincode = request.form['pincode']
    total_slots = int(request.form['total_slots'])
    vehicle_type = request.form.get('vehicle_type', '4-wheeler')
    lot = Mall(name=name, location=location, price=price, address=address,
               pincode=pincode, total_slots=total_slots)
    db.session.add(lot)
    db.session.flush()
    for i in range(1, total_slots+1):
        spot = ParkingSpot(slot_number=f"S{i}", status="Available", mall_id=lot.id, vehicle_type=vehicle_type)
        db.session.add(spot)
    db.session.commit()
    flash('Lot added successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/edit_lot/<int:lot_id>', methods=['GET','POST'])
def edit_lot(lot_id):
    if not is_admin():
        return redirect(url_for('login'))
    lot = Mall.query.get_or_404(lot_id)
    if request.method == 'POST':
        lot.name = request.form['name']
        lot.location = request.form['location']
        lot.price = float(request.form['price'])
        lot.address = request.form['address']
        lot.pincode = request.form['pincode']
        new_slots = int(request.form['total_slots'])
        if new_slots > lot.total_slots:
            for i in range(lot.total_slots + 1, new_slots + 1):
                spot = ParkingSpot(slot_number=f"S{i}", status="Available", mall_id=lot.id, vehicle_type='4-wheeler')
                db.session.add(spot)
        elif new_slots < lot.total_slots:
            needed = lot.total_slots - new_slots
            removable_spots = ParkingSpot.query.filter_by(mall_id=lot.id, status='Available').order_by(ParkingSpot.id.desc()).limit(needed).all()
            if len(removable_spots) < needed:
                flash('Cannot reduce spots: some occupied', 'danger')
                return redirect(url_for('edit_lot', lot_id=lot.id))
            for spot in removable_spots:
                db.session.delete(spot)
        lot.total_slots = new_slots
        db.session.commit()
        flash('Lot updated!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_lot.html', lot=lot)

@app.route('/delete_lot/<int:lot_id>', methods=['POST'])
def delete_lot(lot_id):
    if not is_admin():
        return redirect(url_for('login'))
    lot = Mall.query.get_or_404(lot_id)
    if any(s.status == 'Occupied' for s in lot.spots):
        flash('Cannot delete: Spot occupied', 'danger')
        return redirect(url_for('admin_dashboard'))
    for s in lot.spots:
        db.session.delete(s)
    db.session.delete(lot)
    db.session.commit()
    flash('Lot deleted', 'info')
    return redirect(url_for('admin_dashboard'))

# User routes ---------------------------------------------------------------------

@app.route('/user')
def user_dashboard():
    if not is_logged_in() or is_admin():
        flash('User access only', 'danger')
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    lots = Mall.query.all()
    active_res = Reservation.query.filter_by(user_id=user.id, is_active=True).first()
    past_res = Reservation.query.filter_by(user_id=user.id, is_active=False).order_by(Reservation.start_time.desc()).all()
    return render_template('user.html', user=user, lots=lots, reservation=active_res, past_reservations=past_res)

@app.route('/book_spot', methods=['POST'])
def book_spot():
    if not is_logged_in() or is_admin():
        return redirect(url_for('login'))
    user_id = session['user_id']
    lot_id = int(request.form['lot_id'])
    vehicle_type = request.form.get('vehicle_type', '4-wheeler')
    duration = int(request.form.get('duration_hours', 1))
    if Reservation.query.filter_by(user_id=user_id, is_active=True).first():
        flash('Active reservation exists', 'warning')
        return redirect(url_for('user_dashboard'))
    spot = ParkingSpot.query.filter_by(mall_id=lot_id, vehicle_type=vehicle_type, status='Available').first()
    if not spot:
        flash('No spots available for this vehicle type', 'danger')
        return redirect(url_for('user_dashboard'))
    spot.status = 'Occupied'
    reservation = Reservation(user_id=user_id, spot_id=spot.id, start_time=datetime.utcnow(),
                              is_active=True, duration_hours=duration, vehicle_type=vehicle_type)
    reservation.total_cost = spot.lot.price * duration
    db.session.add(reservation)
    db.session.commit()
    flash('Booked. Show your QR code!', 'success')
    return redirect(url_for('reservation_qr', reservation_id=reservation.id))

@app.route('/release/<int:res_id>')
def release_spot(res_id):
    if not is_logged_in() or is_admin():
        flash('User access only', 'danger')
        return redirect(url_for('login'))
    res = Reservation.query.get_or_404(res_id)
    if res.user_id != session['user_id'] or not res.is_active:
        flash('Invalid reservation', 'danger')
        return redirect(url_for('user_dashboard'))
    res.end_time = datetime.utcnow()
    res.is_active = False
    res.total_cost = calculate_cost(res.start_time, res.end_time, res.spot.lot.price)
    res.spot.status = 'Available'
    db.session.commit()
    flash(f'Spot released. Total charge: ₹{res.total_cost:.2f}', 'info')
    return redirect(url_for('user_dashboard'))

@app.route('/profile', methods=['GET','POST'])
def profile():
    if not is_logged_in():
        flash('Login first', 'warning')
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        user.username = request.form['username']
        new_pw = request.form['password']
        if new_pw.strip():
            user.password = generate_password_hash(new_pw)
        db.session.commit()
        flash('Profile updated', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html', user=user)

@app.route('/reset_password', methods=['GET','POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Email not found', 'danger')
            return render_template('reset_password.html')
        flash('Reset instructions sent to your email (simulated)', 'info')
        return redirect(url_for('login'))
    return render_template('reset_password.html')

@app.route('/reservation_qr/<int:reservation_id>')
def reservation_qr(reservation_id):
    res = Reservation.query.get_or_404(reservation_id)
    data = f"ReservationID:{res.id};User:{res.user.username};Spot:{res.spot.slot_number};Lot:{res.spot.lot.name}"
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf)
    img_b64 = base64.b64encode(buf.getvalue()).decode()
    return render_template('qr_code.html', img_data=img_b64)

@app.route('/feedback/<int:lot_id>', methods=['GET','POST'])
def submit_feedback(lot_id):
    if not is_logged_in():
        flash('Login to submit feedback', 'warning')
        return redirect(url_for('login'))
    lot = Mall.query.get_or_404(lot_id)
    if request.method == 'POST':
        rating = int(request.form['rating'])
        comment = request.form['comment']
        fb = Feedback(user_id=session['user_id'], lot_id=lot.id, rating=rating, comment=comment)
        db.session.add(fb)
        db.session.commit()
        flash('Feedback submitted, thank you!', 'success')
        return redirect(url_for('user_dashboard'))
    return render_template('feedback_form.html', lot=lot)

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/admin/chart_data')
def admin_chart_data():
    if not is_admin():
        return jsonify({'error':'Unauthorized'}), 403
    lots = Mall.query.all()
    labels = [lot.name for lot in lots]
    total_spots = [lot.total_slots for lot in lots]
    occupied_spots = [sum(1 for s in lot.spots if s.status == 'Occupied') for lot in lots]
    return jsonify({'labels': labels, 'total_spots': total_spots, 'occupied_spots': occupied_spots})

@app.route('/user/chart_data')
def user_chart_data():
    if not is_logged_in():
        return jsonify({'error':'Unauthorized'}), 403
    user_id = session['user_id']
    res_list = Reservation.query.filter_by(user_id=user_id, is_active=False).order_by(Reservation.start_time).all()
    labels = [r.start_time.strftime('%d %b') for r in res_list]
    costs = [r.total_cost for r in res_list]
    return jsonify({'labels': labels, 'costs': costs})

if __name__ == '__main__':
    app.run(debug=True)
