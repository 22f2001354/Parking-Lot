from flask import Flask, render_template, redirect, request, session, url_for
from flask import current_app as app 
from .models import *
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64

#==============================================================
# Core Application Routes
#==============================================================

@app.route("/")
def index():
    return render_template("index.html")

#==============================================================
# Authentication Routes
#==============================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        pwd = request.form.get("pwd")
        my_user = User.query.filter_by(email=email).first()
        if my_user and my_user.pwd==pwd:
            if my_user.role == "admin":
                return redirect("/admin")
            else:
                return redirect(url_for("user", user_id = my_user.id))
        else:
            return render_template("login.html", msge="Invalid user id or password !!")
    msgs = request.args.get("msgs")
    return render_template("login.html", msgs=msgs)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        pwd = request.form.get("pwd")
        fullname = request.form.get("fullname")
        address = request.form.get("address")
        pincode = request.form.get("pincode")

        my_user = User.query.filter_by(email=email).first()

        if my_user:
            return render_template("signup.html", msg="User already exist !!")
        else:
            new_user = User(
                email=email,
                pwd=pwd,
                fullname=fullname,
                address=address,
                pincode=pincode
            )
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login', msgs="Registration successful !!"))
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login", msgs="Logout successfully"))

#==============================================================
# Admin Dashboard and Parking Management Routes
#==============================================================

@app.route("/admin")
def admin():
    my_user = User.query.filter_by(role="admin").first()

    all_lots = ParkingLot.query.all()

    return render_template("admin_dash.html", my_user=my_user, all_lots=all_lots)

@app.route("/add_lot", methods=["GET", "POST"])
def add_lot():
    if request.method == "POST":
        name = request.form["location"]
        address = request.form["address"]
        pincode = request.form["pincode"]
        price = float(request.form["price"])
        max_spots = int(request.form["maxispot"])

        new_lot = ParkingLot(
            name=name,
            address=address,
            pincode=pincode,
            price_per_hour=price,
            max_spots=max_spots
        )
        db.session.add(new_lot)
        db.session.commit()

        for _ in range(max_spots):
            spot = ParkingSpot(lot_id=new_lot.id)
            db.session.add(spot)

        db.session.commit()
        return redirect("/admin")

    return render_template("add_lot.html")

@app.route("/edit_parking/<int:parking_id>", methods=["GET", "POST"])
def edit_parking(parking_id):
    parking_lot = ParkingLot.query.get_or_404(parking_id)

    if request.method == "POST":
        parking_lot.name = request.form.get("location")
        parking_lot.address = request.form.get("address")
        parking_lot.pincode = request.form.get("pincode")
        parking_lot.price_per_hour = float(request.form.get("price"))
        new_max_spots = int(request.form.get("maxispot"))

        if new_max_spots > parking_lot.max_spots:
            extra_spots = new_max_spots - parking_lot.max_spots
            for _ in range(extra_spots):
                new_spot = ParkingSpot(lot_id=parking_lot.id)
                db.session.add(new_spot)

        parking_lot.max_spots = new_max_spots
        db.session.commit()
        return redirect("/admin")

    return render_template("edit_parking.html", parking_lot=parking_lot)
@app.route("/delete_parking/<int:parking_id>", methods=["GET", "POST"])
def delete_parking(parking_id):
    parking_lot = ParkingLot.query.get_or_404(parking_id)

    has_occupied_spots = ParkingSpot.query.filter_by(lot_id=parking_lot.id, status="O").count() > 0
    if has_occupied_spots:
        return redirect("/admin")  

    db.session.delete(parking_lot)
    db.session.commit()
    return redirect("/admin")


@app.route("/users")
def users():
    my_user = User.query.filter_by(role="admin").first()
    all_info = ParkingSpot.query.all()  
    all_users = User.query.with_entities(
        User.id,
        User.email,
        User.fullname,
        User.address,
        User.pincode,
        User.role
    ).all()
    return render_template("users.html", users=all_users, my_user=my_user, all_info=all_info)

@app.route("/admin_summary")
def admin_summary():
    all_spots = ParkingSpot.query.all()

    occupied_count = 0
    available_count = 0
    revenue_total = 0

    for spot in all_spots:
        if spot.status == "O":
            occupied_count += 1
        elif spot.status == "A":
            available_count += 1

        for res in spot.reservations:
            if res.released_at:
                cost = res.calculate_cost()
                if cost:
                    revenue_total += cost

    fig1, ax1 = plt.subplots(figsize=(4, 3))
    ax1.bar(['Occupied', 'Available'], [occupied_count, available_count], color=['#EF4444', '#10B981'])
    ax1.set_title("Parking Spot Status")
    fig1.tight_layout()
    buf1 = io.BytesIO()
    fig1.savefig(buf1, format='png')
    buf1.seek(0)
    status_chart = base64.b64encode(buf1.read()).decode('utf-8')
    buf1.close()
    plt.close(fig1)

    fig2, ax2 = plt.subplots(figsize=(4, 3))
    ax2.bar(['Total Revenue'], [revenue_total], color=['#3B82F6'])
    ax2.set_ylim(bottom=0, top=max(10, revenue_total * 1.2)) 
    ax2.set_title("Revenue by Spot Status (₹)")
    fig2.tight_layout()
    buf2 = io.BytesIO()
    fig2.savefig(buf2, format='png')
    buf2.seek(0)
    revenue_chart = base64.b64encode(buf2.read()).decode('utf-8')
    buf2.close()
    plt.close(fig2)

    return render_template(
        "admin_summary.html",
        status_chart=status_chart,
        revenue_chart=revenue_chart
    )

@app.route("/search")
def search():
    my_user = User.query.filter_by(role="admin").first()
    return render_template("search_parking.html", my_user=my_user)

@app.route("/parking_spot/<int:parking_id>")
def parking_spot(parking_id):
    parking_spot = ParkingSpot.query.get_or_404(parking_id)
    now = datetime.now()

    active_reservation = Reservation.query.filter_by(spot_id=parking_spot.id, released_at=None).first()

    if active_reservation:
        booked_user = active_reservation.user

        try:
            price = float(parking_spot.lot.price_per_hour or 0)
        except (ValueError, TypeError):
            price = 0

        duration = now - active_reservation.parked_at
        cost = (duration.total_seconds() / 3600) * price
        duration_str = format_duration(duration)
        cost_str = f"₹{cost:.2f}"

        return render_template("occupied.html",
                       parking_spot=parking_spot,
                       booked_user=booked_user,
                       my_user=booked_user,
                       parked_since=active_reservation.parked_at.strftime('%Y-%m-%d %H:%M'),
                       duration=duration_str,
                       cost=cost_str,
                       vehicle_no=active_reservation.vehicle_no)
    admin_user = User.query.filter_by(role="admin").first()
    return render_template("parking_spot.html", parking_spot=parking_spot, my_user=admin_user)

@app.route("/search_parking", methods=["GET", "POST"])
def search_parking():
    name = request.args.get('name', '')
    max_price = request.args.get('price', type=float)
    pincode = request.args.get('pincode', '')
    status = request.args.get('status', '')  # 'A' or 'O'
    page = request.args.get('page', 1, type=int)

    query = ParkingLot.query

    if name:
        query = query.filter(ParkingLot.name.ilike(f"%{name}%"))
    if max_price is not None:
        query = query.filter(ParkingLot.price_per_hour <= max_price)
    if pincode:
        query = query.filter(ParkingLot.pincode.ilike(f"%{pincode}%"))

    parking_lots_paginated = query.paginate(page=page, per_page=10, error_out=False)

    parking_lots = []
    for lot in parking_lots_paginated.items:
        if status:
            if lot.spots.filter_by(status=status).count() > 0:
                parking_lots.append(lot)
        else:
            parking_lots.append(lot)

    my_user = User.query.filter_by(role="admin").first()

    return render_template(
        "search_parking.html",
        parking_lots=parking_lots,
        my_user=my_user,
        pagination=parking_lots_paginated
    )
#==============================================================
# User Dashboard and Parking Operations Routes
#==============================================================

@app.route("/user/<int:user_id>")
def user(user_id):
    user = User.query.get_or_404(user_id)

    all_lots = ParkingLot.query.all()

    booked_reservations = Reservation.query.filter_by(user_id=user_id).order_by(Reservation.parked_at.desc()).all()

    return render_template(
        "user_dash.html",
        my_user=user,
        all_lots=all_lots,
        booked_lots=booked_reservations
    )


@app.route("/book/<int:parking_id>", methods=["GET", "POST"])
def book(parking_id):
    user_id = request.args.get("user_id")
    if not user_id:
        return "User ID missing in request", 400

    try:
        user_id = int(user_id)
    except ValueError:
        return "Invalid user ID", 400

    parking_spot = ParkingSpot.query.get_or_404(parking_id)
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        vehicle_no = request.form.get("vehicle_no")
        if not vehicle_no:
            return "Vehicle number is required", 400

        if parking_spot.status != "A":
            return "Spot is not available", 400

        parking_spot.status = "O"  

        reservation = Reservation(
            user_id=user_id,
            spot_id=parking_spot.id,
            vehicle_no=vehicle_no,
            parked_at=datetime.utcnow()
        )

        db.session.add(reservation)
        db.session.commit()

        return redirect(url_for("user", user_id=user_id))

    return render_template("book.html", parking_lot=parking_spot, user_id=user_id, user=user)


@app.route("/release/<int:parking_id>/<int:user_id>",methods=["POST"])
def release(parking_id, user_id):
    parking_spot = ParkingSpot.query.get_or_404(parking_id)

    parking_spot.status = "A"  

    reservation = Reservation.query.filter_by(user_id=user_id, spot_id=parking_id, released_at=None).first()
    if reservation:
        reservation.released_at = datetime.utcnow()

    db.session.commit()
    return redirect(url_for("user", user_id=user_id))


@app.route("/park_out/<int:parking_id>/<int:user_id>")
def park_out(parking_id, user_id):
    parking_spot = ParkingSpot.query.get_or_404(parking_id)
    reservation = Reservation.query.filter_by(user_id=user_id, spot_id=parking_id, released_at=None).first()
    
    now = datetime.utcnow()
    cost = 0

    if reservation and reservation.parked_at:
        time_diff = now - reservation.parked_at
        hours = max(1, int(time_diff.total_seconds() // 3600))
        cost = hours * parking_spot.lot.price_per_hour 

    return render_template(
    "release.html",
    parking_lot=parking_spot,
    reservation=reservation,
    user_id=user_id,
    now=now.strftime('%Y-%m-%d %H:%M'),
    total_cost=round(cost, 2)
)
from collections import Counter

@app.route("/user_summary/<int:user_id>")
def user_summary(user_id):
    my_user = User.query.get_or_404(user_id)
    reservations = Reservation.query.filter_by(user_id=user_id).all()
    lot_names = [res.spot.lot.name for res in reservations]
    lot_counter = Counter(lot_names)
    labels = list(lot_counter.keys())
    values = list(lot_counter.values())
    fig, ax = plt.subplots(figsize=(6, 3))
    bars = ax.bar(labels, values, color="#93C5FD", edgecolor="black")
    ax.set_title("Parking Frequency by Lot")
    ax.set_ylabel("Times Parked")
    ax.bar_label(bars)
    fig.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    chart_data = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.close(fig)
    total_bookings = sum(values)
    unique_lots = len(labels)

    return render_template("user_summary.html",
                           my_user=my_user,
                           chart_data=chart_data,
                           total_bookings=total_bookings,
                           unique_lots=unique_lots,
                           lot_list=labels)

@app.route('/profile/<int:user_id>', methods=['GET', 'POST'])
def profile(user_id):
    my_user = User.query.get(user_id)

    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')

        if fullname:
            my_user.fullname = fullname
        if email:
            my_user.email = email
        if password:
            my_user.pwd = password

        db.session.commit()
        return redirect(f'/profile/{user_id}')

    return render_template('profile.html', my_user=my_user)
#==============================================================
# Helper Functions
#==============================================================

def format_duration(timedelta):
    total_seconds = int(timedelta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes}m"