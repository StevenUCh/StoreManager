from app import app, db
from sqlalchemy import text

def fix_alembic_version():
    with app.app_context():
        try:
            # Verificar si existe la tabla alembic_version
            result = db.session.execute(
                text("SELECT tablename FROM pg_tables WHERE tablename='alembic_version';")
            ).fetchone()
            
            if not result:
                print("⚠️  La tabla 'alembic_version' no existe. Nada que limpiar.")
                return

            # Ver el contenido actual
            version = db.session.execute(
                text("SELECT version_num FROM alembic_version;")
            ).fetchone()

            print(f"📋 Versión actual de Alembic: {version[0] if version else 'No hay registros.'}")

            # Borrar la versión antigua
            db.session.execute(text("DELETE FROM alembic_version;"))
            db.session.commit()

            print("✅ Registro de versión eliminado correctamente.")
            print("👉 Ahora puedes ejecutar: flask db stamp head && flask db upgrade")

        except Exception as e:
            print(f"❌ Error al limpiar la tabla alembic_version: {e}")

if __name__ == "__main__":
    fix_alembic_version()

