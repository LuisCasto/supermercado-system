"""
Script para generar hashes de contraseñas con bcrypt
Ejecutar: python generate_password_hash.py
"""
import bcrypt

def generate_hash(password):
    """Genera hash bcrypt de una contraseña"""
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')

def verify_hash(password, hashed):
    """Verifica si una contraseña coincide con un hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

if __name__ == '__main__':
    # Generar hash para password123
    password = 'password123'
    
    print("=" * 60)
    print("GENERADOR DE HASHES BCRYPT")
    print("=" * 60)
    
    # Generar 3 hashes diferentes (bcrypt usa salt aleatorio)
    print(f"\nContraseña: {password}")
    print("\nHashes generados (cada uno es único debido al salt):\n")
    
    for i in range(3):
        hash_result = generate_hash(password)
        print(f"Hash {i+1}:")
        print(hash_result)
        
        # Verificar
        is_valid = verify_hash(password, hash_result)
        print(f"✓ Verificación: {'OK' if is_valid else 'FAILED'}\n")
    
    print("=" * 60)
    print("ACTUALIZACIÓN DEL SEED SQL")
    print("=" * 60)
    
    # Generar uno para usar en el seed
    final_hash = generate_hash(password)
    
    print(f"\nUsa este hash en 03_seed_data.sql:\n")
    print(f"'{final_hash}'")
    
    print("\n" + "=" * 60)
    print("VERIFICAR HASH EXISTENTE")
    print("=" * 60)
    
    # Verificar el hash que está en tu seed actual
    old_hash = '$2b$12$AnehbzfVpf1otpAHlI6bh.SMG5Webavps1u.d.bCwwVZTAbPoL7mq'
    print(f"\nHash actual en seed: {old_hash}")
    
    # Probar diferentes contraseñas
    test_passwords = ['password123', 'password', '123456', 'admin123']
    
    print("\nProbando contraseñas contra el hash del seed:")
    for pwd in test_passwords:
        is_match = verify_hash(pwd, old_hash)
        status = "✓ MATCH" if is_match else "✗ No coincide"
        print(f"  {pwd:15s} -> {status}")
    
    print("\n" + "=" * 60)