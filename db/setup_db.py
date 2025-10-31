# setup_db.py

import os
import subprocess

if __name__ == "__main__":
    db_url = os.environ.get('DATABASE_URL')
    
    if not db_url:
        print("ERROR: La variable de entorno DATABASE_URL no está configurada.")
        exit(1)
        
    print("--- Verificando e inicializando el esquema de Supabase (PostgreSQL) ---")
    
    try:
        # Ejecuta el comando 'flask init-db' definido en app.py
        # Esto llamará a db.create_all()
        subprocess.run(['flask', 'init-db'], check=True)
        print("--- Esquema de base de datos inicializado/verificado correctamente. ---")
        
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar la inicialización de la base de datos: {e}")
        print("Asegúrate de que la URI de Supabase y el SECRET_KEY sean correctos.")
        exit(1)
    except FileNotFoundError:
        print("Error: El comando 'flask' no se encuentra. ¿Estás en un entorno virtual activo o en Render?")
        exit(1)