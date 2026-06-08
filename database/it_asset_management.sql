CREATE DATABASE IF NOT EXISTS it_asset_management;
USE it_asset_management;

-- Users
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user'
);

-- Categories
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT
);

-- Assets
CREATE TABLE IF NOT EXISTS assets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_tag VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    brand VARCHAR(100),
    model VARCHAR(100),
    serial_number VARCHAR(100),
    category_id INT,
    status VARCHAR(50) DEFAULT 'Active',
    location VARCHAR(100),
    purchase_date DATE,
    warranty_expiration DATE,
    notes TEXT,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- Technicians
CREATE TABLE IF NOT EXISTS technicians (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(50)
);

-- Interventions
CREATE TABLE IF NOT EXISTS interventions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_id INT,
    technician_id INT,
    description TEXT,
    intervention_date DATE,
    FOREIGN KEY (asset_id) REFERENCES assets(id),
    FOREIGN KEY (technician_id) REFERENCES technicians(id)
);

-- Admin por defeito
INSERT IGNORE INTO users (username, name, email, password, role)
VALUES ('admin', 'Admin', 'admin@evolve.com', 'admin123', 'admin');

-- Categorias de exemplo
INSERT IGNORE INTO categories (name, description) VALUES
('Laptops', 'Portáteis e notebooks'),
('Desktops', 'Computadores de secretária'),
('Monitors', 'Monitores e ecrãs'),
('Printers', 'Impressoras e scanners'),
('Networking', 'Switches, routers e cabos');

-- Técnicos de exemplo
INSERT IGNORE INTO technicians (name, email, phone) VALUES
('João Silva', 'joao@evolve.com', '912 000 001'),
('Maria Santos', 'maria@evolve.com', '912 000 002'),
('Carlos Ferreira', 'carlos@evolve.com', '912 000 003');