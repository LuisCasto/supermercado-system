-- Crear usuario para la aplicación con privilegios mínimos
CREATE USER app_user WITH PASSWORD 'apppass123';

-- Otorgar permisos de conexión
GRANT CONNECT ON DATABASE supermercado_db TO app_user;

-- Otorgar permisos sobre el schema public
GRANT USAGE ON SCHEMA public TO app_user;

-- Otorgar permisos sobre todas las tablas
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;

-- Otorgar permisos sobre secuencias (para SERIAL/AUTO INCREMENT)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Asegurar que los permisos se apliquen a tablas futuras
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_user;