# WattWise — Electricity Consumption and Smart Meter Management System

A Flask + SQLAlchemy academic DBMS project demonstrating consumer records, meter registration, readings, bills, simulated payments, alerts, authentication, and role-based access.

## Run locally
1. Install Python 3.10+.
2. Create and activate a virtual environment.
3. Run `pip install -r requirements.txt`.
4. Set a strong `SECRET_KEY` environment variable for any shared deployment.
5. Run `python app.py`.
6. Open `http://127.0.0.1:5000`.

The app creates its schema and inserts demo data on startup.

## Demo accounts
- Admin: `admin@smartmeter.demo` / `Admin123!`
- Consumer: `aarav@example.com` / `Consumer123!`

Change passwords and secret configuration before public deployment. This demo does not process real payments or connect to physical smart meters.

## Technology
- Flask (web framework)
- Flask-SQLAlchemy (ORM)
- SQLite locally; PostgreSQL can be used by setting `DATABASE_URL`
- Jinja templates + responsive CSS
- Werkzeug password hashing
- Gunicorn for hosting

## Database tables (8)
Roles, Users, Consumers, Meters, Readings, Bills, Payments, Alerts, AuditLogs (9 tables).
Each table has a primary key and relevant foreign keys. Unique constraints protect emails, account numbers and meter serial numbers.

## Deployment (Render)
1. Push this folder to a private GitHub repository.
2. On Render, create a new Web Service and connect the repository.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add environment variables `SECRET_KEY` and `DATABASE_URL` using a managed PostgreSQL instance.
6. Before public use, change the demo credentials and add production security controls.

A live URL is only created after deployment from your hosting account. No external deployment account was available during project generation.
