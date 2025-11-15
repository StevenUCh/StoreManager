
import os
import subprocess
from datetime import datetime

def get_latest_backup():
    """Encuentra el último archivo de backup en /backups."""
    backup_dir = os.path.join(os.getcwd(), "backups")

    if not os.path.exists(backup_dir):
        raise FileNotFoundError("❌ El directorio /backups no existe.")

    files = [f for f in os.listdir(backup_dir) if f.endswith(".sql")]

    if not files:
        raise FileNotFoundError("❌ No hay archivos .sql en la carpeta /backups")

    # Ordenar por fecha usando el nombre del archivo
    files.sort(reverse=True)
    return os.path.join(backup_dir, files[0])


def restore_backup(backup_path=None):
    """Restaura un archivo .sql usando psql."""
    db_url = "postgresql://postgres:UEzpqzxDbWtGmKANoqKhvUVodrjBpATA@shuttle.proxy.rlwy.net:10542/railway" #os.getenv("DATABASE_URL")

    if not db_url:
        raise ValueError("❌ No se encontró DATABASE_URL en las variables de entorno.")

    # Normalizar URL de SQLAlchemy → PostgreSQL
    if db_url.startswith("postgresql+psycopg2://"):
        db_url = db_url.replace("postgresql+psycopg2://", "postgresql://")

    # Si no se pasa un archivo, usar el último
    if not backup_path:
        backup_path = get_latest_backup()

    print(f"🔄 Restaurando base desde: {backup_path}")

    try:
        subprocess.run(
            ["psql", db_url, "-f", backup_path],
            check=True
        )
        print("✅ Restauración completada con éxito.")
    except Exception as e:
        print(f"❌ Error al restaurar la base de datos: {e}")
        raise


if __name__ == "__main__":
    restore_backup()   # Restaura el último backup automáticamente




# import os
# from datetime import datetime
# from backup import backup_database   # Importa la función desde tu script principal

# def run_backup():
#     """
#     Ejecuta ÚNICAMENTE el backup de la base de datos.
#     No limpia, no crea tablas, no sincroniza modelos.
#     Solo hace el respaldo.
#     """
#     print("🚀 Iniciando proceso de backup...")

#     try:
#         backup_file = backup_database()
#         print(f"✅ Backup completado exitosamente.")
#         print(f"📂 Archivo generado: {backup_file}")

#     except Exception as e:
#         print(f"❌ Error al realizar el backup: {e}")


# if __name__ == "__main__":
#     run_backup()
