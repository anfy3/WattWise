import os
from datetime import datetime, date
from decimal import Decimal
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-before-deployment")
db_url = os.getenv("DATABASE_URL", "sqlite:///smart_meter.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    role = db.relationship("Role")

class Consumer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    account_number = db.Column(db.String(30), unique=True, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    tariff_rate = db.Column(db.Numeric(8,2), nullable=False, default=6.50)
    user = db.relationship("User")

class Meter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    consumer_id = db.Column(db.Integer, db.ForeignKey("consumer.id"), nullable=False)
    meter_serial = db.Column(db.String(50), unique=True, nullable=False)
    installation_date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(20), nullable=False, default="Active")
    consumer = db.relationship("Consumer")

class Reading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meter_id = db.Column(db.Integer, db.ForeignKey("meter.id"), nullable=False)
    reading_date = db.Column(db.Date, nullable=False, default=date.today)
    units_kwh = db.Column(db.Numeric(10,2), nullable=False)
    meter = db.relationship("Meter")

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    consumer_id = db.Column(db.Integer, db.ForeignKey("consumer.id"), nullable=False)
    billing_month = db.Column(db.String(7), nullable=False)
    units_kwh = db.Column(db.Numeric(10,2), nullable=False)
    amount = db.Column(db.Numeric(12,2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Unpaid")
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    consumer = db.relationship("Consumer")

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey("bill.id"), nullable=False)
    amount_paid = db.Column(db.Numeric(12,2), nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    method = db.Column(db.String(30), nullable=False, default="Demo")
    bill = db.relationship("Bill")

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meter_id = db.Column(db.Integer, db.ForeignKey("meter.id"), nullable=False)
    message = db.Column(db.String(250), nullable=False)
    severity = db.Column(db.String(20), nullable=False, default="Info")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, nullable=False, default=False)
    meter = db.relationship("Meter")

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    entity = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        user = db.session.get(User, session["user_id"])
        if not user or user.role.name != "Admin":
            flash("Administrator access is required.", "danger")
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_user():
    user = db.session.get(User, session.get("user_id")) if session.get("user_id") else None
    return {"current_user": user}

@app.route("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter(func.lower(User.email) == request.form.get("email","").lower().strip()).first()
        if user and check_password_hash(user.password_hash, request.form.get("password","")):
            session.clear()
            session["user_id"] = user.id
            db.session.add(AuditLog(user_id=user.id, action="Login", entity="User"))
            db.session.commit()
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    uid = session.get("user_id")
    if uid:
        db.session.add(AuditLog(user_id=uid, action="Logout", entity="User"))
        db.session.commit()
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    total_consumers = Consumer.query.count()
    total_meters = Meter.query.count()
    total_units = db.session.query(func.coalesce(func.sum(Reading.units_kwh), 0)).scalar()
    unpaid = Bill.query.filter_by(status="Unpaid").count()
    latest_readings = Reading.query.order_by(Reading.reading_date.desc(), Reading.id.desc()).limit(6).all()
    alerts = Alert.query.filter_by(resolved=False).order_by(Alert.created_at.desc()).limit(5).all()
    return render_template("dashboard.html", total_consumers=total_consumers, total_meters=total_meters,
        total_units=total_units, unpaid=unpaid, latest_readings=latest_readings, alerts=alerts)

@app.route("/consumers", methods=["GET", "POST"])
@login_required
def consumers():
    if request.method == "POST":
        try:
            name=request.form["full_name"].strip()
            email=request.form["email"].strip().lower()
            account=request.form["account_number"].strip()
            if not name or not email or not account:
                raise ValueError("Name, email and account number are required.")
            role=Role.query.filter_by(name="Consumer").first()
            user=User(full_name=name,email=email,password_hash=generate_password_hash(request.form.get("password") or "ChangeMe123!"),role=role)
            db.session.add(user); db.session.flush()
            consumer=Consumer(user_id=user.id,account_number=account,address=request.form["address"].strip(),
                              tariff_rate=Decimal(request.form.get("tariff_rate") or "6.50"))
            db.session.add(consumer)
            db.session.add(AuditLog(user_id=session["user_id"],action="Create consumer",entity="Consumer"))
            db.session.commit()
            flash("Consumer added. Default/demo password is ChangeMe123! if none was entered.", "success")
            return redirect(url_for("consumers"))
        except Exception as exc:
            db.session.rollback(); flash("Could not add consumer: " + str(exc), "danger")
    q=request.args.get("q","").strip()
    query=Consumer.query.join(User)
    if q:
        query=query.filter((User.full_name.ilike(f"%{q}%")) | (Consumer.account_number.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%")))
    page=max(int(request.args.get("page",1)),1); per_page=8
    pagination=query.order_by(Consumer.id.desc()).paginate(page=page,per_page=per_page,error_out=False)
    return render_template("consumers.html", pagination=pagination, q=q)

@app.route("/meters", methods=["GET", "POST"])
@login_required
def meters():
    if request.method=="POST":
        try:
            meter=Meter(consumer_id=int(request.form["consumer_id"]),meter_serial=request.form["meter_serial"].strip(),
                        installation_date=date.fromisoformat(request.form["installation_date"]),status=request.form["status"])
            db.session.add(meter); db.session.add(AuditLog(user_id=session["user_id"],action="Create meter",entity="Meter")); db.session.commit()
            flash("Meter added successfully.","success"); return redirect(url_for("meters"))
        except Exception as exc:
            db.session.rollback(); flash("Could not add meter: "+str(exc),"danger")
    return render_template("meters.html", meters=Meter.query.order_by(Meter.id.desc()).all(), consumers=Consumer.query.all())

@app.route("/readings", methods=["GET", "POST"])
@login_required
def readings():
    if request.method=="POST":
        try:
            units=Decimal(request.form["units_kwh"])
            if units < 0: raise ValueError("Units cannot be negative.")
            r=Reading(meter_id=int(request.form["meter_id"]),reading_date=date.fromisoformat(request.form["reading_date"]),units_kwh=units)
            db.session.add(r); db.session.flush()
            meter=db.session.get(Meter,r.meter_id); consumer=meter.consumer
            month=r.reading_date.strftime("%Y-%m")
            amount=(units * Decimal(consumer.tariff_rate)).quantize(Decimal("0.01"))
            bill=Bill(consumer_id=consumer.id,billing_month=month,units_kwh=units,amount=amount,status="Unpaid")
            db.session.add(bill)
            db.session.add(AuditLog(user_id=session["user_id"],action="Add reading and generate bill",entity="Reading"))
            db.session.commit()
            flash(f"Reading saved and demo bill generated: ₹{amount}.","success"); return redirect(url_for("readings"))
        except Exception as exc:
            db.session.rollback(); flash("Could not save reading: "+str(exc),"danger")
    return render_template("readings.html", readings=Reading.query.order_by(Reading.reading_date.desc()).all(), meters=Meter.query.filter_by(status="Active").all())

@app.route("/bills", methods=["GET", "POST"])
@login_required
def bills():
    if request.method=="POST":
        try:
            bill=db.session.get(Bill,int(request.form["bill_id"]))
            if bill and bill.status=="Unpaid":
                with db.session.begin_nested():
                    payment=Payment(bill_id=bill.id,amount_paid=bill.amount,method=request.form.get("method","Demo"))
                    db.session.add(payment); bill.status="Paid"
                    db.session.add(AuditLog(user_id=session["user_id"],action="Record demo payment",entity="Bill"))
                db.session.commit(); flash("Demo payment recorded; no real money was transferred.","success")
            return redirect(url_for("bills"))
        except Exception as exc:
            db.session.rollback(); flash("Payment action failed: "+str(exc),"danger")
    q=request.args.get("q","").strip()
    query=Bill.query.join(Consumer).join(User)
    if q: query=query.filter((User.full_name.ilike(f"%{q}%")) | (Bill.billing_month.ilike(f"%{q}%")) | (Bill.status.ilike(f"%{q}%")))
    return render_template("bills.html", bills=query.order_by(Bill.id.desc()).all(), q=q)

@app.route("/alerts", methods=["GET", "POST"])
@login_required
def alerts():
    if request.method=="POST":
        a=db.session.get(Alert,int(request.form["alert_id"]))
        if a: a.resolved=True; db.session.commit(); flash("Alert marked resolved.","success")
        return redirect(url_for("alerts"))
    return render_template("alerts.html", alerts=Alert.query.order_by(Alert.resolved,Alert.created_at.desc()).all(), meters=Meter.query.all())

@app.route("/alerts/create", methods=["POST"])
@login_required
def create_alert():
    try:
        db.session.add(Alert(meter_id=int(request.form["meter_id"]),message=request.form["message"].strip(),
                             severity=request.form["severity"]))
        db.session.add(AuditLog(user_id=session["user_id"],action="Create alert",entity="Alert"))
        db.session.commit(); flash("Alert created.","success")
    except Exception as exc:
        db.session.rollback(); flash("Could not create alert: "+str(exc),"danger")
    return redirect(url_for("alerts"))

@app.route("/admin/users")
@admin_required
def users():
    return render_template("users.html", users=User.query.order_by(User.id).all())

@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="The page you requested was not found."),404

@app.errorhandler(500)
def server_error(e):
    db.session.rollback()
    return render_template("error.html", code=500, message="An unexpected error occurred. Please try again."),500

def seed():
    db.create_all()
    for role_name in ["Admin","Consumer"]:
        if not Role.query.filter_by(name=role_name).first(): db.session.add(Role(name=role_name))
    db.session.commit()
    if User.query.count()==0:
        admin_role=Role.query.filter_by(name="Admin").first()
        consumer_role=Role.query.filter_by(name="Consumer").first()
        admin=User(full_name="Demo Administrator",email="admin@smartmeter.demo",
                   password_hash=generate_password_hash(os.getenv("DEMO_ADMIN_PASSWORD","Admin123!")),role=admin_role)
        user=User(full_name="Aarav Nair",email="aarav@example.com",
                  password_hash=generate_password_hash("Consumer123!"),role=consumer_role)
        db.session.add_all([admin,user]); db.session.flush()
        c=Consumer(user_id=user.id,account_number="SM-10001",address="Vellore, Tamil Nadu",tariff_rate=Decimal("6.50"))
        db.session.add(c); db.session.flush()
        m=Meter(consumer_id=c.id,meter_serial="MTR-90001",installation_date=date(2026,1,15),status="Active")
        db.session.add(m); db.session.flush()
        db.session.add_all([
            Reading(meter_id=m.id,reading_date=date(2026,10,1),units_kwh=Decimal("128.50")),
            Reading(meter_id=m.id,reading_date=date(2026,10,15),units_kwh=Decimal("146.20")),
            Bill(consumer_id=c.id,billing_month="2026-10",units_kwh=Decimal("146.20"),amount=Decimal("950.30"),status="Unpaid"),
            Alert(meter_id=m.id,message="Consumption is higher than the previous period.",severity="Medium")
        ])
        db.session.commit()

with app.app_context():
    seed()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",5000)), debug=False)
