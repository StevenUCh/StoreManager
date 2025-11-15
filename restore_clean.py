import os
import subprocess
from sqlalchemy import create_engine, inspect, text

def drop_all_tables(db_url):
    """Elimina todas las tablas existentes (CASCADE) antes de restaurar."""
    engine = create_engine(db_url)

    with engine.connect() as connection:
        inspector = inspect(connection)
        tables = inspector.get_table_names()

        print("🗑 Tables a eliminar:", tables)

        # Desactivar FK checks temporalmente
        connection.execute(text("SET session_replication_role = 'replica';"))

        for table in tables:
            print(f"❌ Dropping {table} ...")
            connection.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE;'))

        # Reactivar FK checks
        connection.execute(text("SET session_replication_role = 'origin';"))

        print("✅ Todas las tablas eliminadas correctamente.")


def restore_backup(backup_path):
    """Restaura el archivo SQL sobre una base vacía."""
    db_url = "postgresql://postgres:UEzpqzxDbWtGmKANoqKhvUVodrjBpATA@shuttle.proxy.rlwy.net:10542/railway"

    if not db_url:
        raise ValueError("DATABASE_URL no está configurada.")

    # Normalizar SQLAlchemy URL
    if db_url.startswith("postgresql+psycopg2://"):
        db_url = db_url.replace("postgresql+psycopg2://", "postgresql://")

    print(f"🔄 Restaurando backup desde: {backup_path}")

    subprocess.run(["psql", db_url, "-f", backup_path], check=True)

    print("✅ Restauración exitosa con base limpia.")


def restore_clean(backup_path):
    """Proceso completo: DROP + RESTORE."""
    db_url = "postgresql://postgres:UEzpqzxDbWtGmKANoqKhvUVodrjBpATA@shuttle.proxy.rlwy.net:10542/railway"

    drop_all_tables(db_url)
    restore_backup(backup_path)


if __name__ == "__main__":
    backup_file = r"backups/backup_20251114_193223.sql"
    restore_clean(backup_file)
