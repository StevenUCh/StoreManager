import os
import subprocess
from datetime import datetime
from sqlalchemy import text, inspect
from app import app, db

# $env:Path += ";C:\Program Files\PostgreSQL\17\bin"
# py backup.py

def backup_database():
    """Genera un backup completo de la base PostgreSQL usando pg_dump."""
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        raise ValueError("❌ No se encontró DATABASE_URL en las variables de entorno.")

    # Parsear la URL si viene con el prefijo de SQLAlchemy (postgresql+psycopg2://)
    if db_url.startswith("postgresql+psycopg2://"):
        db_url = db_url.replace("postgresql+psycopg2://", "postgresql://")

    # Nombre del archivo de backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(os.getcwd(), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, f"backup_{timestamp}.sql")

    print(f"💾 Generando backup en: {backup_path}")

    try:
        # Ejecutar pg_dump con credenciales de la URL
        subprocess.run(
            ["pg_dump", db_url, "-f", backup_path],
            check=True
        )
        print("✅ Backup creado correctamente.")
    except Exception as e:
        print(f"⚠️ Error al generar el backup: {e}")
        raise

    return backup_path


def sync_and_clean_database():
    """Crea backup, limpia tablas y sincroniza con los modelos."""
    with app.app_context():
        # 1️⃣ Backup antes de limpiar
        backup_path = backup_database()

        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        model_tables = list(db.metadata.tables.keys())

        print("📊 Tablas actuales en BD:", existing_tables)
        print("📘 Tablas definidas en modelos:", model_tables)

        # 2️⃣ Limpiar datos de todas las tablas
        print("🧹 Limpiando todas las tablas...")
        for table in existing_tables:
            db.session.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE;'))
        db.session.commit()
        print("✅ Datos eliminados correctamente.")

        # 3️⃣ Crear tablas que falten
        missing_tables = [t for t in model_tables if t not in existing_tables]
        if missing_tables:
            print("🧱 Creando tablas faltantes:", missing_tables)
            db.create_all()
        else:
            print("📦 No hay tablas faltantes.")

        print(f"✅ Base de datos sincronizada y limpia. Backup guardado en {backup_path}")


if __name__ == "__main__":
    backup_database()
