import os
import subprocess
import psycopg2
from urllib.parse import urlparse
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# ==============================================
# CONFIGURACIÓN
# ==============================================

CONNECTION_STRING = "postgresql://postgres:UEzpqzxDbWtGmKANoqKhvUVodrjBpATA@shuttle.proxy.rlwy.net:10542/railway"
BACKUP_FILE = "backups/backup_20251114_193223.sql"


# ---- Parsear connection string ----
def parse_conn_str(conn_str):
    url = urlparse(conn_str)

    return {
        "user": url.username,
        "password": url.password,
        "host": url.hostname,
        "port": url.port,
        "database": url.path.lstrip("/")
    }


cfg = parse_conn_str(CONNECTION_STRING)

PG_USER = cfg["user"]
PG_PASSWORD = cfg["password"]
PG_HOST = cfg["host"]
PG_PORT = str(cfg["port"])
DATABASE_NAME = cfg["database"]


# ==============================================
# FUNCIONES
# ==============================================

def drop_database():
    """Elimina la base completa."""
    print(f"🗑 Eliminando base de datos '{DATABASE_NAME}' ...")

    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=PG_USER,
            password=PG_PASSWORD,
            host=PG_HOST,
            port=PG_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        cur.execute(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{DATABASE_NAME}';
        """)

        cur.execute(f"DROP DATABASE IF EXISTS {DATABASE_NAME};")

        cur.close()
        conn.close()

        print("✅ Base eliminada correctamente.")
    except Exception as e:
        print(f"❌ Error eliminando la base: {e}")


def create_database():
    """Crea la base nuevamente."""
    print(f"🧱 Creando base de datos '{DATABASE_NAME}' ...")

    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=PG_USER,
            password=PG_PASSWORD,
            host=PG_HOST,
            port=PG_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        cur.execute(f"CREATE DATABASE {DATABASE_NAME};")

        cur.close()
        conn.close()

        print("✅ Base creada correctamente.")
    except Exception as e:
        print(f"❌ Error creando la base: {e}")


def restore_backup():
    """Importa el backup usando psql."""
    print(f"🔄 Restaurando backup desde: {BACKUP_FILE}")

    if not os.path.exists(BACKUP_FILE):
        print("❌ No existe el archivo de backup.")
        return

    env = os.environ.copy()
    env["PGPASSWORD"] = PG_PASSWORD

    try:
        subprocess.run(
            [
                "psql",
                "-U", PG_USER,
                "-h", PG_HOST,
                "-p", PG_PORT,
                "-d", DATABASE_NAME,
                "-f", BACKUP_FILE
            ],
            env=env,
            check=True
        )
        print("✅ Backup restaurado exitosamente.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error restaurando backup: {e}")


# ==============================================
# MAIN
# ==============================================

if __name__ == "__main__":
    print("🚀 Proceso de restauración FULL iniciado")

    drop_database()
    create_database()
    restore_backup()

    print("🎉 Proceso COMPLETADO con éxito")
