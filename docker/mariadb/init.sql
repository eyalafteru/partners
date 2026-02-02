-- PartnerCalc OS - MariaDB Initialization
-- This script runs once when the container is first created

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS partnercalc 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

-- Create user and grant privileges
-- Note: Password should match MYSQL_PASSWORD in docker-compose
CREATE USER IF NOT EXISTS 'partnercalc'@'%' IDENTIFIED BY 'partnercalc123';
GRANT ALL PRIVILEGES ON partnercalc.* TO 'partnercalc'@'%';
FLUSH PRIVILEGES;

-- Use the database
USE partnercalc;

-- Tables are created automatically by SQLAlchemy on app startup
-- This file only handles database and user creation

-- Optional: Create tables manually if needed (backup of schema)
-- The actual tables are created by: backend/app/database.py -> init_db()
