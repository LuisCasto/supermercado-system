// ===============================================
// Script de Inicialización: Sistema Supermercado
// Autor: Luis A
// Fecha: 2025-12-01
// ===============================================
// IMPORTANTE: Este script se ejecuta SOLO si /data/db está vacío
// Si necesitas re-ejecutarlo, elimina el volumen con:
// docker volume rm supermercado-system_mongo_data
// ===============================================

print("========================================");
print("Iniciando configuración de MongoDB");
print("========================================");

// ===============================================
// 1. VERIFICAR/CREAR USUARIO ROOT
// ===============================================
// NOTA: Si usas MONGO_INITDB_ROOT_USERNAME en docker-compose,
// Docker ya crea este usuario. Este bloque es por si acaso.

db = db.getSiblingDB("admin");

try {
  // Intentar obtener info del usuario admin
  const adminUser = db.getUser("admin");
  
  if (adminUser) {
    print("✓ Usuario root 'admin' ya existe (creado por Docker)");
  } else {
    print("→ Creando usuario root 'admin'...");
    db.createUser({
      user: "admin",
      pwd: "admin123",
      roles: [
        { role: "root", db: "admin" }
      ]
    });
    print("✓ Usuario root 'admin' creado");
  }
} catch (e) {
  print("⚠ Error al verificar/crear usuario root:");
  print(e.message);
}

// ===============================================
// 2. CREAR BASE DE DATOS DEL PROYECTO
// ===============================================

print("\n→ Configurando base de datos 'supermercado_sales'...");
db = db.getSiblingDB("supermercado_sales");

// ===============================================
// 3. CREAR COLECCIÓN CON VALIDACIÓN
// ===============================================

print("→ Creando colección 'sales_tickets' con validación...");

try {
  db.createCollection("sales_tickets", {
    validator: {
      $jsonSchema: {
        bsonType: "object",
        required: ["sale_id", "cashier_id", "items", "total", "timestamp"],
        properties: {
          sale_id: {
            bsonType: "string",
            description: "ID único de la venta - requerido"
          },
          cashier_id: {
            bsonType: "int",
            minimum: 1,
            description: "ID del cajero - requerido"
          },
          cashier_name: {
            bsonType: "string",
            description: "Nombre del cajero"
          },
          items: {
            bsonType: "array",
            minItems: 1,
            description: "Lista de productos vendidos - requerido",
            items: {
              bsonType: "object",
              required: ["product_id", "quantity", "unit_price", "subtotal"],
              properties: {
                product_id: {
                  bsonType: "int",
                  description: "ID del producto"
                },
                product_name: {
                  bsonType: "string"
                },
                sku: {
                  bsonType: "string"
                },
                batch_id: {
                  bsonType: "int"
                },
                quantity: {
                  bsonType: "int",
                  minimum: 1
                },
                unit_price: {
                  bsonType: "double",
                  minimum: 0
                },
                subtotal: {
                  bsonType: "double",
                  minimum: 0
                }
              }
            }
          },
          total: {
            bsonType: "double",
            minimum: 0,
            description: "Total de la venta - requerido"
          },
          tax: {
            bsonType: "double",
            minimum: 0
          },
          grand_total: {
            bsonType: "double",
            minimum: 0
          },
          payment_method: {
            enum: ["cash", "card", "transfer", "other"],
            description: "Método de pago"
          },
          payment_details: {
            bsonType: "object"
          },
          status: {
            enum: ["completed", "cancelled", "refunded"],
            description: "Estado de la venta"
          },
          timestamp: {
            bsonType: "date",
            description: "Fecha y hora de la venta - requerido"
          },
          created_at: {
            bsonType: "date",
            description: "Fecha de registro en MongoDB"
          }
        }
      }
    },
    validationLevel: "moderate", // No falla si faltan campos opcionales
    validationAction: "warn"     // Solo advierte, no rechaza documentos
  });
  print("✓ Colección 'sales_tickets' creada con validación JSON Schema");
} catch (e) {
  if (e.codeName === "NamespaceExists") {
    print("✓ Colección 'sales_tickets' ya existe");
  } else {
    print("⚠ Error al crear colección:");
    print(e.message);
  }
}

// ===============================================
// 4. CREAR ÍNDICES OPTIMIZADOS
// ===============================================

print("→ Creando índices para optimizar consultas...");

try {
  // Índice único para sale_id (evita duplicados)
  db.sales_tickets.createIndex(
    { "sale_id": 1 }, 
    { unique: true, name: "idx_sale_id_unique" }
  );
  print("✓ Índice único en 'sale_id'");

  // Índice compuesto para consultas por cajero y fecha
  db.sales_tickets.createIndex(
    { "cashier_id": 1, "timestamp": -1 }, 
    { name: "idx_cashier_timestamp" }
  );
  print("✓ Índice compuesto 'cashier_id + timestamp'");

  // Índice para consultas por fecha (reportes)
  db.sales_tickets.createIndex(
    { "timestamp": -1 }, 
    { name: "idx_timestamp_desc" }
  );
  print("✓ Índice en 'timestamp'");

  // Índice para búsquedas por producto
  db.sales_tickets.createIndex(
    { "items.product_id": 1 }, 
    { name: "idx_items_product_id" }
  );
  print("✓ Índice en 'items.product_id'");

  // Índice para consultas por estado
  db.sales_tickets.createIndex(
    { "status": 1 }, 
    { name: "idx_status" }
  );
  print("✓ Índice en 'status'");

} catch (e) {
  print("⚠ Error al crear índices:");
  print(e.message);
}

// ===============================================
// 5. CREAR USUARIO DE APLICACIÓN
// ===============================================

print("\n→ Creando usuario 'app_user' para la aplicación...");

try {
  db.createUser({
    user: "app_user",
    pwd: "apppass123",
    roles: [
      { 
        role: "readWrite", 
        db: "supermercado_sales" 
      }
    ],
    customData: {
      description: "Usuario para la aplicación Flask del supermercado",
      created: new Date()
    }
  });
  print("✓ Usuario 'app_user' creado con permisos readWrite");
} catch (e) {
  if (e.codeName === "DuplicateKey" || e.code === 51003) {
    print("✓ Usuario 'app_user' ya existe");
  } else {
    print("⚠ Error al crear usuario:");
    print(e.message);
  }
}

// ===============================================
// 6. INSERTAR DATOS DE PRUEBA
// ===============================================

print("\n→ Insertando documento de prueba...");

try {
  const testSale = {
    sale_id: "SALE-INIT-2025-001",
    cashier_id: 1,
    cashier_name: "Sistema (Inicialización)",
    items: [
      {
        product_id: 1,
        product_name: "Leche Entera 1L",
        sku: "LAC-001",
        batch_id: 1,
        quantity: 2,
        unit_price: 25.50,
        subtotal: 51.00
      },
      {
        product_id: 3,
        product_name: "Pan Blanco",
        sku: "PAN-010",
        batch_id: 4,
        quantity: 1,
        unit_price: 18.00,
        subtotal: 18.00
      }
    ],
    total: 69.00,
    tax: 11.04,
    grand_total: 80.04,
    payment_method: "cash",
    payment_details: {
      amount_paid: 100.00,
      change: 19.96
    },
    status: "completed",
    timestamp: new Date(),
    created_at: new Date()
  };

  db.sales_tickets.insertOne(testSale);
  print("✓ Documento de prueba insertado (sale_id: SALE-INIT-2025-001)");
} catch (e) {
  if (e.code === 11000) {
    print("✓ Documento de prueba ya existe");
  } else {
    print("⚠ Error al insertar documento de prueba:");
    print(e.message);
  }
}

// ===============================================
// 7. VERIFICACIÓN FINAL
// ===============================================

print("\n========================================");
print("Verificación final:");
print("========================================");

// Contar documentos
const docCount = db.sales_tickets.countDocuments();
print(`✓ Documentos en 'sales_tickets': ${docCount}`);

// Listar índices
const indexes = db.sales_tickets.getIndexes();
print(`✓ Índices creados: ${indexes.length}`);
indexes.forEach(idx => {
  print(`  - ${idx.name}`);
});

// Verificar usuarios
db = db.getSiblingDB("supermercado_sales");
const users = db.getUsers();
print(`✓ Usuarios creados: ${users.users.length}`);
users.users.forEach(user => {
  print(`  - ${user.user} (roles: ${user.roles.map(r => r.role).join(", ")})`);
});

print("\n========================================");
print("✓ Inicialización completada exitosamente");
print("========================================");
print("\nConexión para la aplicación:");
print("mongodb://app_user:apppass123@localhost:27017/supermercado_sales?authSource=supermercado_sales");
print("\nConexión admin:");
print("mongodb://admin:admin123@localhost:27017/?authSource=admin");
print("========================================\n");