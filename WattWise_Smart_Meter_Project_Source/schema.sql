-- Relational schema reference (the running app creates equivalent tables via SQLAlchemy ORM)
CREATE TABLE Roles (
  id INTEGER PRIMARY KEY,
  name VARCHAR(30) NOT NULL UNIQUE
);
CREATE TABLE Users (
  id INTEGER PRIMARY KEY,
  full_name VARCHAR(100) NOT NULL,
  email VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role_id INTEGER NOT NULL REFERENCES Roles(id),
  created_at TIMESTAMP NOT NULL
);
CREATE TABLE Consumers (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES Users(id),
  account_number VARCHAR(30) NOT NULL UNIQUE,
  address VARCHAR(200) NOT NULL,
  tariff_rate DECIMAL(8,2) NOT NULL DEFAULT 6.50 CHECK (tariff_rate > 0)
);
CREATE TABLE Meters (
  id INTEGER PRIMARY KEY,
  consumer_id INTEGER NOT NULL REFERENCES Consumers(id),
  meter_serial VARCHAR(50) NOT NULL UNIQUE,
  installation_date DATE NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'Active'
);
CREATE TABLE Readings (
  id INTEGER PRIMARY KEY,
  meter_id INTEGER NOT NULL REFERENCES Meters(id),
  reading_date DATE NOT NULL,
  units_kwh DECIMAL(10,2) NOT NULL CHECK (units_kwh >= 0)
);
CREATE TABLE Bills (
  id INTEGER PRIMARY KEY,
  consumer_id INTEGER NOT NULL REFERENCES Consumers(id),
  billing_month CHAR(7) NOT NULL,
  units_kwh DECIMAL(10,2) NOT NULL CHECK (units_kwh >= 0),
  amount DECIMAL(12,2) NOT NULL CHECK (amount >= 0),
  status VARCHAR(20) NOT NULL DEFAULT 'Unpaid',
  issued_at TIMESTAMP
);
CREATE TABLE Payments (
  id INTEGER PRIMARY KEY,
  bill_id INTEGER NOT NULL REFERENCES Bills(id),
  amount_paid DECIMAL(12,2) NOT NULL CHECK (amount_paid >= 0),
  payment_date TIMESTAMP,
  method VARCHAR(30) NOT NULL
);
CREATE TABLE Alerts (
  id INTEGER PRIMARY KEY,
  meter_id INTEGER NOT NULL REFERENCES Meters(id),
  message VARCHAR(250) NOT NULL,
  severity VARCHAR(20) NOT NULL DEFAULT 'Info',
  created_at TIMESTAMP,
  resolved BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE TABLE AuditLogs (
  id INTEGER PRIMARY KEY,
  user_id INTEGER REFERENCES Users(id),
  action VARCHAR(100) NOT NULL,
  entity VARCHAR(50) NOT NULL,
  created_at TIMESTAMP
);
CREATE INDEX idx_readings_meter_date ON Readings(meter_id, reading_date);
CREATE INDEX idx_bills_status_month ON Bills(status, billing_month);
CREATE INDEX idx_alerts_resolved_created ON Alerts(resolved, created_at);
