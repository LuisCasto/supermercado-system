-- Eliminar tablas si existen (para desarrollo)
DROP TABLE IF EXISTS inventory_movements CASCADE;
DROP TABLE IF EXISTS outbox_events CASCADE;
DROP TABLE IF EXISTS product_batches CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Tabla: users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('gerente', 'inventario', 'cajero')),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);

-- Tabla: products
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    base_price NUMERIC(10,2) NOT NULL CHECK (base_price > 0),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_name ON products(name);
CREATE INDEX idx_products_category ON products(category);

-- Tabla: product_batches
CREATE TABLE product_batches (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    batch_code VARCHAR(100) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    cost_per_unit NUMERIC(10,2) NOT NULL CHECK (cost_per_unit > 0),
    expiration_date DATE,
    received_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, batch_code)
);

CREATE INDEX idx_batches_product_id ON product_batches(product_id);
CREATE INDEX idx_batches_expiration ON product_batches(expiration_date);

-- Tabla: inventory_movements
CREATE TABLE inventory_movements (
    id SERIAL PRIMARY KEY,
    product_batch_id INTEGER NOT NULL REFERENCES product_batches(id) ON DELETE CASCADE,
    movement_type VARCHAR(20) NOT NULL CHECK (movement_type IN ('ENTRY', 'SALE', 'ADJUSTMENT', 'EXPIRATION')),
    quantity INTEGER NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    reference_id VARCHAR(100),
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_movements_batch ON inventory_movements(product_batch_id);
CREATE INDEX idx_movements_user ON inventory_movements(user_id);
CREATE INDEX idx_movements_created ON inventory_movements(created_at);

-- Tabla: outbox_events
CREATE TABLE outbox_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    aggregate_id VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

CREATE INDEX idx_outbox_status_created ON outbox_events(status, created_at);
CREATE INDEX idx_outbox_aggregate ON outbox_events(aggregate_id);

-- Trigger para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comentarios en tablas
COMMENT ON TABLE users IS 'Usuarios del sistema con roles RBAC';
COMMENT ON TABLE products IS 'Catálogo de productos del supermercado';
COMMENT ON TABLE product_batches IS 'Lotes de productos con fechas de vencimiento';
COMMENT ON TABLE inventory_movements IS 'Auditoría de movimientos de inventario';
COMMENT ON TABLE outbox_events IS 'Patrón Outbox para consistencia eventual';