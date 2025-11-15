import psycopg2

# ========================
# TU CONNECTION STRING
# ========================
DATABASE_URL = "postgresql://postgres:UEzpqzxDbWtGmKANoqKhvUVodrjBpATA@shuttle.proxy.rlwy.net:10542/railway"


# ========================
# FUNCIONES
# ========================
def clean_amount_fields():
    """Elimina los decimales de todas las columnas Float relevantes."""
    print("🚀 Iniciando limpieza de montos...")

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # Lista explícita de columnas a limpiar (según tus modelos)
    updates = [
        ('movimiento', 'monto'),
        ('detalle_movimiento', 'monto'),
        ('detalle_movimiento', 'abonado'),
        ('detalle_movimiento', 'falta'),
        ('abono', 'monto'),
        ('abono_indirecto', 'monto_aplicado'),
        ('saldo_favor', 'monto'),
    ]

    for table, column in updates:
        print(f"➡️ Actualizando {table}.{column} ...")
        cur.execute(f'UPDATE "{table}" SET "{column}" = TRUNC("{column}");')

    print("🎉 Limpieza completada sin errores.")

    cur.close()
    conn.close()


# ========================
# MAIN
# ========================
if __name__ == "__main__":
    clean_amount_fields()
