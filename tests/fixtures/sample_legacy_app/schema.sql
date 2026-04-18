-- InventoryPro Legacy Database Schema
-- PostgreSQL 11 (target: upgrade to 16)
-- Last modified: 2023-08-14 by Dave

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    email VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    failed_attempts INTEGER DEFAULT 0,
    last_failed_at TIMESTAMPTZ,
    last_login TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
-- NOTE: no updated_at column on users table
-- NOTE: no audit trail for user changes

CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255),
    phone VARCHAR(50),
    api_endpoint VARCHAR(500),
    api_type VARCHAR(20) DEFAULT 'none',
    lead_time_days INTEGER DEFAULT 7,
    rating DECIMAL(3,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    parent_id INTEGER,
    description TEXT,
    FOREIGN KEY (parent_id) REFERENCES categories(id)
);
-- NOTE: no created_at/updated_at on categories
-- NOTE: no index on parent_id for hierarchical queries

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    sku VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    cost DECIMAL(10, 2),
    quantity INTEGER NOT NULL DEFAULT 0,
    min_stock INTEGER DEFAULT 10,
    category_id INTEGER,
    supplier_id INTEGER,
    warehouse_location VARCHAR(100),
    barcode VARCHAR(100),
    weight_kg DECIMAL(8, 3),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);
-- NOTE: no index on category_id (frequently filtered)
-- NOTE: no index on supplier_id (frequently joined)
-- NOTE: no index on warehouse_location (warehouse staff queries)
-- NOTE: barcode column has no UNIQUE constraint

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    total_amount DECIMAL(12, 2) NOT NULL,
    discount DECIMAL(10, 2) DEFAULT 0,
    tax DECIMAL(10, 2) DEFAULT 0,
    notes TEXT,
    approved_by INTEGER,
    approved_at TIMESTAMPTZ,
    shipped_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    tracking_number VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (approved_by) REFERENCES users(id)
);
-- NOTE: no updated_at column
-- NOTE: no index on status (frequently filtered)
-- NOTE: no index on created_at (used in date-range reports)
-- NOTE: no cost_center column (finance requirement from meeting)

CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    line_total DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
-- NOTE: no created_at column
-- NOTE: no index on order_id (always joined)

CREATE TABLE reorder_requests (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    supplier_id INTEGER,
    quantity INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    unit_cost DECIMAL(10, 2),
    estimated_delivery TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);
-- NOTE: no created_by / approved_by tracking on reorder requests
-- NOTE: no audit trail for status changes

CREATE TABLE inventory_adjustments (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    adjusted_by INTEGER NOT NULL,
    previous_quantity INTEGER NOT NULL,
    new_quantity INTEGER NOT NULL,
    reason TEXT,
    adjustment_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (adjusted_by) REFERENCES users(id)
);
-- This table provides SOME audit trail for manual adjustments
-- but does NOT capture changes made via order processing or reorders

-- Only indexes that exist in production:
CREATE UNIQUE INDEX idx_users_username ON users(username);
CREATE UNIQUE INDEX idx_products_sku ON products(sku);
