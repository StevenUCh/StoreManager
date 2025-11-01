Perfecto 👍 Aquí tienes el bloque completo que puedes pegar directamente en tu **`README.md`** (explicativo, limpio y en formato profesional).

---

## 🧱 Gestión de Migraciones con Flask-Migrate (SQLAlchemy + Alembic)

El proyecto usa **Flask-Migrate** para mantener sincronizados los modelos (`models.py`) con la base de datos PostgreSQL.
Esto permite agregar, modificar o eliminar columnas sin perder los datos existentes.

---

### 🚀 Inicialización (solo la primera vez)

```bash
flask db init
```

Este comando crea la carpeta `migrations/`, que almacena el historial de versiones del esquema de la base de datos.

---

### ⚙️ Crear y aplicar cambios

Cada vez que modifiques un modelo (por ejemplo, agregas o cambias columnas), ejecuta los siguientes comandos:

```bash
flask db migrate -m "Descripción del cambio (por ejemplo: Agregar campo pago_todo a DetalleMovimiento)"
flask db upgrade
```

* `flask db migrate` genera un nuevo archivo de migración en `migrations/versions/` con los cambios detectados.
* `flask db upgrade` aplica esos cambios a la base de datos activa.

👉 **Importante:** estos comandos **no borran los datos**, solo actualizan la estructura.

---

### 🔁 Revertir una migración (volver a la versión anterior)

Si una migración genera errores o afecta la estructura de forma incorrecta, puedes revertirla fácilmente:

```bash
flask db downgrade
```

* Este comando revierte **solo la última migración aplicada**.
* Puedes usar un identificador de versión específico para volver más atrás:

  ```bash
  flask db downgrade <id_de_version>
  ```
* Para regresar al estado inicial (sin migraciones aplicadas):

  ```bash
  flask db downgrade base
  ```

Luego de corregir tus modelos, simplemente vuelve a generar y aplicar una nueva migración:

```bash
flask db migrate -m "Corrección del modelo"
flask db upgrade
```

---

### 🕒 ¿Cada cuánto se ejecuta?

* **Después de cada cambio en tus modelos** (`models.py` o módulos equivalentes).
* **Antes de desplegar** una nueva versión del sistema en entornos de prueba o producción.
* **Nunca es necesario hacerlo diariamente**, solo cuando el modelo cambia.

---

### 💾 Recomendación

Antes de aplicar migraciones importantes, haz un **backup** de la base usando:

```bash
pg_dump -h <host> -U <usuario> -d <nombre_base> -f backup_pre_migracion.sql
```

Así podrás restaurar fácilmente si algo sale mal.

---

¿Quieres que te genere también el bloque adicional con **cómo automatizar las migraciones** (por ejemplo, ejecutar `migrate + upgrade` al iniciar la app en modo desarrollo)?
