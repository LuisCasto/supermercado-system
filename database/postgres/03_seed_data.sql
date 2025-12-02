-- Insertar usuarios de prueba (password: 'password123' hasheado con bcrypt)
INSERT INTO users (username, email, hashed_password, role) VALUES
('gerente1', 'gerente@supermercado.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lk7qa8v0nRKK', 'gerente'),
('inventario1', 'inventario@supermercado.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lk7qa8v0nRKK', 'inventario'),
('cajero1', 'cajero1@supermercado.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lk7qa8v0nRKK', 'cajero'),
('cajero2', 'cajero2@supermercado.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lk7qa8v0nRKK', 'cajero');

-- Insertar productos de ejemplo
INSERT INTO products (sku, name, description, category, base_price) VALUES
('LAC-001', 'Leche Entera 1L', 'Leche entera pasteurizada', 'Lácteos', 25.50),
('LAC-002', 'Yogurt Natural 1kg', 'Yogurt natural sin azúcar', 'Lácteos', 45.00),
('PAN-010', 'Pan Blanco', 'Pan blanco tradicional', 'Panadería', 18.00),
('BEB-001', 'Agua Natural 1.5L', 'Agua purificada', 'Bebidas', 12.00),
('BEB-002', 'Refresco Cola 2L', 'Bebida carbonatada', 'Bebidas', 28.00),
('FRU-001', 'Manzana Red Delicious kg', 'Manzana fresca', 'Frutas', 35.00),
('VER-001', 'Lechuga Romana', 'Lechuga fresca', 'Verduras', 22.00),
('CAR-001', 'Carne Molida kg', 'Carne de res molida', 'Carnicería', 120.00);

-- Insertar lotes de productos
INSERT INTO product_batches (product_id, batch_code, quantity, cost_per_unit, expiration_date, received_date) VALUES
(1, 'LOTE-LAC-2025-01', 100, 18.00, '2025-12-15', '2025-11-20'),
(1, 'LOTE-LAC-2025-02', 50, 18.50, '2025-12-20', '2025-11-25'),
(2, 'LOTE-YOG-2025-01', 80, 32.00, '2025-12-10', '2025-11-18'),
(3, 'LOTE-PAN-2025-01', 200, 12.00, '2025-11-30', '2025-11-28'),
(4, 'LOTE-AGU-2025-01', 300, 8.00, '2026-06-01', '2025-11-01'),
(5, 'LOTE-REF-2025-01', 150, 20.00, '2026-03-01', '2025-11-15'),
(6, 'LOTE-FRU-2025-01', 50, 25.00, '2025-12-05', '2025-11-27'),
(7, 'LOTE-VER-2025-01', 40, 15.00, '2025-12-01', '2025-11-27'),
(8, 'LOTE-CAR-2025-01', 30, 95.00, '2025-12-03', '2025-11-26');

-- Insertar movimientos iniciales (entradas)
INSERT INTO inventory_movements (product_batch_id, movement_type, quantity, user_id, note) VALUES
(1, 'ENTRY', 100, 2, 'Recepción de mercancía - Proveedor A'),
(2, 'ENTRY', 50, 2, 'Recepción de mercancía - Proveedor A'),
(3, 'ENTRY', 80, 2, 'Recepción de mercancía - Proveedor B'),
(4, 'ENTRY', 200, 2, 'Recepción de mercancía - Panadería Local'),
(5, 'ENTRY', 300, 2, 'Recepción de mercancía - Embotelladora'),
(6, 'ENTRY', 150, 2, 'Recepción de mercancía - Distribuidora'),
(7, 'ENTRY', 50, 2, 'Recepción de mercancía - Mercado Local'),
(8, 'ENTRY', 40, 2, 'Recepción de mercancía - Mercado Local'),
(9, 'ENTRY', 30, 2, 'Recepción de mercancía - Carnicería Central');