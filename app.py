import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_file, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models.users import db, User, Person, SaldoFavor
from models.move import Movimiento, DetalleMovimiento, Abono, AbonoIndirecto
from forms.forms import LoginForm, RegisterForm, PersonForm, MovimientoForm
import csv
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import logging
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from flask_migrate import Migrate

load_dotenv()

logger = logging.getLogger(__name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


# -------------------------
# Helpers
# -------------------------

def parse_amount(value, default=0):
    """Parsea un string que puede contener comas y puntos decimales
    y lo convierte a entero redondeando correctamente. Devuelve int.

    - Acepta None, '' → retorna default
    - Elimina comas de miles
    - Si value no es numérico, lanza ValueError
    """
    if value is None:
        return int(default)
    if isinstance(value, (int, float)):
        return int(round(value))
    s = str(value).strip()
    if s == "":
        return int(default)

    # Normalizar separadores (asume que coma puede ser separador de miles)
    s = s.replace(',', '')
    try:
        return int(round(float(s)))
    except Exception as e:
        raise ValueError(f"Monto inválido: {value}") from e


def format_currency_int(value):
    """Formatea un entero como moneda: $1,234"""
    try:
        v = int(round(value or 0))
    except Exception:
        v = 0
    return "${:,.0f}".format(v)


# -------------------------
# App factory
# -------------------------

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or 'dev'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL') or 'sqlite:///' + os.path.join(BASE_DIR, 'db', 'database.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    Migrate(app, db)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except Exception:
            return None

    # -------------------------
    # Template filters
    # -------------------------
    @app.template_filter('currency')
    def currency_filter(value):
        return format_currency_int(value)

    # -------------------------
    # Routes
    # -------------------------
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    # Auth
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        form = RegisterForm()
        if form.validate_on_submit():
            existing_user = User.query.filter_by(username=form.username.data).first()
            if existing_user:
                flash('El usuario ya existe', 'warning')
                return redirect(url_for('register'))

            u = User(username=form.username.data, password=generate_password_hash(form.password.data))
            db.session.add(u)
            db.session.commit()

            login_user(u)
            flash(f'Bienvenido, {u.username}! Tu cuenta ha sido creada.', 'success')
            return redirect(url_for('dashboard'))
        return render_template('register.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('dashboard'))
            flash('Credenciales inválidas', 'danger')
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    # Dashboard
    @app.route('/dashboard')
    @login_required
    def dashboard():
        page = request.args.get("page", 1, type=int)
        per_page = 10

        pagination = Movimiento.query \
            .filter_by(user_id=current_user.id) \
            .order_by(Movimiento.fecha.desc()) \
            .paginate(page=page, per_page=per_page)

        movimientos = prepare_movimientos_saldo(pagination.items)

        all_movs = Movimiento.query.filter_by(user_id=current_user.id).all()

        ingresos = sum(int(m.monto) for m in all_movs if m.tipo == 'ingreso')
        gastos = sum(int(m.monto) for m in all_movs if m.tipo == 'gasto')
        pagos = sum(int(m.monto) for m in all_movs if m.tipo == 'pago')
        balance = ingresos - gastos

        ingresos_gastos_data = {
            'labels': [m.fecha.strftime('%d/%m') for m in all_movs],
            'ingresos': [int(m.monto) for m in all_movs if m.tipo == 'ingreso'],
            'gastos': [int(m.monto) for m in all_movs if m.tipo == 'gasto'],
        }

        categorias = {}
        for m in all_movs:
            if m.tipo == 'gasto':
                categorias[m.categoria] = categorias.get(m.categoria, 0) + int(m.monto)

        categorias_data = {
            'labels': list(categorias.keys()),
            'valores': list(categorias.values()),
        }

        # --- Deudas por persona ---
        persons = Person.query.filter_by(user_id=current_user.id).all()
        deudas = []
        total_deuda = 0

        for p in persons:
            total_monto = 0
            total_abonos = 0
            total_le_deben = 0

            for d in p.detalles:
                if d.movimiento.user_id != current_user.id:
                    continue

                abonos_sum = sum(int(a.monto) for a in d.abonos)
                total_monto += int(d.monto)
                total_abonos += abonos_sum

                if getattr(d, 'pago_todo', False):
                    otros_detalles = DetalleMovimiento.query.filter(
                        DetalleMovimiento.movimiento_id == d.movimiento_id,
                        DetalleMovimiento.persona_id != p.id,
                    ).all()

                    for od in otros_detalles:
                        abonos_od = sum(int(a.monto) for a in od.abonos)
                        deuda_od = max(int(od.monto) - abonos_od, 0)
                        total_le_deben += deuda_od

            saldo_favor_total = db.session.query(
                db.func.coalesce(db.func.sum(SaldoFavor.monto), 0)
            ).filter_by(persona_id=p.id, user_id=current_user.id).scalar() or 0

            total_debe = max(total_monto - total_abonos, 0)
            balance_person = total_le_deben - total_debe + int(saldo_favor_total)

            total_deuda += total_debe

            deudas.append({
                'person': p,
                'debe': total_debe,
                'pagado': total_abonos,
                'le_deben': total_le_deben,
                'saldo_favor': int(saldo_favor_total),
                'balance': balance_person,
            })

        return render_template(
            'dashboard.html',
            movimientos=movimientos,
            pagination=pagination,
            ingresos=ingresos,
            gastos=gastos,
            pagos=pagos,
            balance=balance,
            deudas=deudas,
            ingresos_gastos_data=ingresos_gastos_data,
            categorias_data=categorias_data,
            total_deuda=total_deuda,
        )

    @app.route('/dashboard/table')
    @login_required
    def dashboard_table():
        page = request.args.get("page", 1, type=int)
        per_page = 10

        pagination = Movimiento.query \
            .filter_by(user_id=current_user.id) \
            .order_by(Movimiento.fecha.desc()) \
            .paginate(page=page, per_page=per_page)

        movimientos = prepare_movimientos_saldo(pagination.items)  # función reutilizable

        return render_template("dashboard_table.html",
                            movimientos=movimientos,
                            pagination=pagination)
    
    def prepare_movimientos_saldo(movimientos):
        """Prepara la lista de movimientos con su saldo faltante."""
        data = []

        for mov in movimientos:
            total_falta = 0

            for det in mov.detalles:
                abonos_sum = sum(int(a.monto) for a in det.abonos)
                falta_detalle = int(det.monto) - abonos_sum
                total_falta += max(falta_detalle, 0)

            data.append({
                'id': mov.id,
                'fecha': mov.fecha,
                'tipo': mov.tipo,
                'categoria': mov.categoria,
                'descripcion': mov.descripcion,
                'monto': int(mov.monto),
                'falta': total_falta,
            })

        return data

    # Personas
    @app.route('/personas', methods=['GET', 'POST'])
    @login_required
    def personas():
        form = PersonForm()
        if form.validate_on_submit():
            p = Person(name=form.name.data.strip(), user_id=current_user.id)
            db.session.add(p)
            db.session.commit()
            flash('Persona agregada', 'success')
            return redirect(url_for('personas'))
        persons = Person.query.filter_by(user_id=current_user.id).all()
        return render_template('personas.html', form=form, persons=persons)

    @app.route('/personas/delete/<int:person_id>', methods=['POST'])
    @login_required
    def person_delete(person_id):
        p = Person.query.filter_by(id=person_id, user_id=current_user.id).first_or_404()
        tiene_detalles = bool(p.detalles)
        tiene_abonos = any(d.abonos for d in p.detalles)
        if tiene_detalles or tiene_abonos:
            flash('No puedes eliminar esta persona porque tiene registros asociados a movimientos o abonos.', 'danger')
            return redirect(url_for('personas'))
        db.session.delete(p)
        db.session.commit()
        flash('Persona eliminada correctamente.', 'success')
        return redirect(url_for('personas'))

    # Movimientos
    @app.route('/movimientos', methods=['GET', 'POST'])
    @login_required
    def movimientos():
        form = MovimientoForm()
        persons = Person.query.filter_by(user_id=current_user.id).all()

        desde = request.args.get('desde')
        hasta = request.args.get('hasta')
        query = Movimiento.query.filter_by(user_id=current_user.id)
        if desde:
            try:
                d = datetime.fromisoformat(desde).date()
                query = query.filter(Movimiento.fecha >= d)
            except Exception as e:
                logger.warning(f"Fecha desde inválida: {desde} → {e}")
        if hasta:
            try:
                h = datetime.fromisoformat(hasta).date()
                query = query.filter(Movimiento.fecha <= h)
            except Exception as e:
                logger.warning(f"Fecha hasta inválida: {hasta} → {e}")

        movimientos_list = query.order_by(Movimiento.fecha.desc()).all()

        if request.method == 'POST':
            try:
                tipo = request.form.get('tipo', '').strip()
                categoria = request.form.get('categoria', '').strip()
                descripcion = request.form.get('descripcion', '').strip()
                monto_raw = request.form.get('monto', '0')
                fecha_raw = request.form.get('fecha', '').strip()

                if not tipo or not categoria or not monto_raw or not fecha_raw:
                    flash('Por favor completa todos los campos obligatorios.', 'danger')
                    return render_template('movimientos.html', form=form, movimientos=movimientos_list, persons=persons, desde=desde or '', hasta=hasta or '')

                monto = parse_amount(monto_raw)
                fecha = datetime.strptime(fecha_raw, '%Y-%m-%d').date()

                movimiento = Movimiento(tipo=tipo, categoria=categoria, descripcion=descripcion, monto=monto, fecha=fecha, user_id=current_user.id)
                db.session.add(movimiento)
                db.session.flush()

                for p in persons:
                    key_m = f"monto_{p.id}"
                    key_a = f"abonado_{p.id}"
                    key_e = f"estado_{p.id}"

                    monto_persona_raw = request.form.get(key_m, '').strip()
                    if not monto_persona_raw:
                        continue
                    try:
                        monto_persona = parse_amount(monto_persona_raw)
                        abonado = parse_amount(request.form.get(key_a, '0'))
                        estado = request.form.get(key_e, 'Debe')
                        pago_key = f"pago_{p.id}"

                        detalle = DetalleMovimiento(
                            persona_id=p.id,
                            movimiento_id=movimiento.id,
                            monto=monto_persona,
                            abonado=0,
                            falta=monto_persona,
                            estado=estado,
                        )
                        detalle.pago_todo = request.form.get(pago_key) == '1'
                        db.session.add(detalle)
                        db.session.flush()

                        if abonado > 0:
                            abono_inicial = Abono(detalle_id=detalle.id, monto=abonado, fecha=datetime.combine(fecha, datetime.min.time()))
                            db.session.add(abono_inicial)
                            db.session.flush()

                        total_abonos = sum(int(a.monto) for a in detalle.abonos)
                        detalle.abonado = total_abonos
                        detalle.falta = max(int(detalle.monto) - total_abonos, 0)
                        detalle.estado = 'Pagado' if detalle.falta == 0 else 'Debe'

                        db.session.commit()
                    except ValueError as ve:
                        logger.warning(f"Error parseando monto/abonado para {p.name}: {ve}")
                        continue

                db.session.commit()
                flash('Movimiento creado correctamente.', 'success')
                return redirect(url_for('movimientos'))
            except Exception as e:
                db.session.rollback()
                logger.exception('Error guardando movimiento')
                flash(f'Error al guardar movimiento: {e}', 'danger')

        return render_template('movimientos.html', form=form, movimientos=movimientos_list, persons=persons, desde=desde or '', hasta=hasta or '')

    @app.route('/movimiento/<int:mov_id>', methods=['GET', 'POST'])
    @login_required
    def movimiento_detail(mov_id):
        abono_id = request.args.get('abono_id', type=int)
        abono = None
        movimientos_deudor = []

        m = Movimiento.query.filter_by(id=mov_id, user_id=current_user.id).first_or_404()
        pagador_todo = next((d for d in m.detalles if d.pago_todo), None)
        deuda_total = 0
        if pagador_todo:
            for d in m.detalles:
                if d.id != pagador_todo.id:
                    abonado_total = d.abonado + sum(int(a.monto) for a in d.abonos)
                    deuda_total += max(int(d.monto) - abonado_total, 0)

        if abono_id:
            abono = Abono.query.get(abono_id)
            if abono:
                session['ultimo_abono_monto'] = int(abono.monto)

            if pagador_todo:
                movimientos_deudor = [
                    {
                        'movimiento_id': d.movimiento_id,
                        'categoria': m.categoria,
                        'descripcion': m.descripcion,
                        'falta': int(d.falta),
                    }
                    for d, m in db.session.query(DetalleMovimiento, Movimiento)
                    .filter(
                        DetalleMovimiento.persona_id == pagador_todo.persona_id,
                        DetalleMovimiento.falta > 0,
                        DetalleMovimiento.movimiento_id == Movimiento.id,
                    )
                ]

        return render_template('deuda_detalle.html', mov=m, pagador_todo=pagador_todo, deuda_total=deuda_total, abono=abono, movimientos_deudor=movimientos_deudor, abono_monto=session.get('ultimo_abono_monto'))

    @app.route('/movimiento/delete/<int:mov_id>', methods=['POST'])
    @login_required
    def movimiento_delete(mov_id):
        movimiento = Movimiento.query.filter_by(id=mov_id, user_id=current_user.id).first_or_404()
        db.session.delete(movimiento)
        db.session.commit()
        flash('Movimiento y todos sus registros asociados eliminados correctamente.', 'success')
        return redirect(url_for('movimientos'))

    @app.route('/api/detalle/<int:detalle_id>/toggle', methods=['POST'])
    @login_required
    def toggle_detalle(detalle_id):
        d = DetalleMovimiento.query.join(Movimiento).filter(DetalleMovimiento.id == detalle_id, Movimiento.user_id == current_user.id).first_or_404()
        d.estado = 'Pagado' if d.estado == 'Debe' else 'Debe'
        db.session.commit()
        return jsonify({'status': 'ok', 'estado': d.estado})

    @app.route('/movimiento/<int:mov_id>/abonar', methods=['POST'])
    @login_required
    def abonar(mov_id):
        mov = Movimiento.query.filter_by(id=mov_id, user_id=current_user.id).first_or_404()
        detalle_id = request.form.get('detalle_id')
        monto_str = request.form.get('monto', '0')
        fecha_str = request.form.get('fecha', '').strip()
        usar_saldo = request.form.get('usar_saldo', 'no')

        try:
            monto = parse_amount(monto_str)
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Datos inválidos. Revisa el monto y la fecha.', 'error')
            return redirect(url_for('movimiento_detail', mov_id=mov_id))

        detalle = DetalleMovimiento.query.filter_by(id=detalle_id, movimiento_id=mov.id).first_or_404()
        persona = detalle.person

        saldo_actual = db.session.query(db.func.coalesce(db.func.sum(SaldoFavor.monto), 0)).filter_by(persona_id=persona.id).scalar() or 0
        saldo_actual = int(saldo_actual)

        if usar_saldo == 'si':
            if saldo_actual <= 0:
                flash(f'{persona.name} no tiene saldo a favor disponible.', 'error')
                return redirect(url_for('movimiento_detail', mov_id=mov.id))
            if monto > saldo_actual:
                flash(f'El saldo disponible de {persona.name} ({format_currency_int(saldo_actual)}) es insuficiente.', 'error')
                return redirect(url_for('movimiento_detail', mov_id=mov.id))

            registro_saldo = SaldoFavor(persona_id=persona.id, user_id=current_user.id, monto=-monto, fecha=fecha_obj, comentario=f'Uso de saldo a favor en movimiento #{mov.id}')
            db.session.add(registro_saldo)

        nuevo_abono = Abono(detalle_id=detalle.id, monto=monto, fecha=fecha_obj)
        db.session.add(nuevo_abono)
        db.session.flush()

        total_abonos = sum(int(a.monto) for a in detalle.abonos)
        detalle.abonado = total_abonos
        detalle.falta = max(int(detalle.monto) - total_abonos, 0)
        detalle.estado = 'Pagado' if detalle.falta == 0 else 'Debe'

        db.session.commit()

        if usar_saldo == 'si':
            flash(f'Abono de {format_currency_int(monto)} registrado usando saldo a favor.', 'success')
        else:
            flash(f'Abono de {format_currency_int(monto)} registrado correctamente.', 'success')

        return redirect(url_for('movimiento_detail', mov_id=mov.id, abono_id=nuevo_abono.id))

    @app.route('/abono/<int:abono_id>/delete', methods=['POST'])
    @login_required
    def delete_abono(abono_id):
        abono = Abono.query.get_or_404(abono_id)
        detalle = abono.detalle
        mov = detalle.movimiento
        persona = detalle.person
        mov_id = detalle.movimiento_id

        if hasattr(abono, 'indirectos'):
            for indirecto in abono.indirectos:
                db.session.delete(indirecto)

        uso_saldo = SaldoFavor.query.filter(
            SaldoFavor.persona_id == persona.id,
            SaldoFavor.user_id == current_user.id,
            SaldoFavor.monto == -abono.monto,
            SaldoFavor.comentario.like(f'%movimiento #{mov.id}%'),
        ).first()

        if uso_saldo:
            reversion = SaldoFavor(persona_id=persona.id, user_id=current_user.id, monto=abono.monto, fecha=datetime.utcnow(), comentario=f'Reversión de uso de saldo por eliminación de abono #{abono.id} del movimiento #{mov.id}')
            db.session.add(reversion)

        detalle.abonado = max(int(detalle.abonado) - int(abono.monto), 0)
        detalle.estado = 'Pagado' if detalle.abonado >= detalle.monto else 'Debe'

        db.session.delete(abono)
        db.session.commit()

        flash('Abono eliminado correctamente. Se revirtió el saldo si aplicaba.', 'success')
        return redirect(url_for('movimiento_detail', mov_id=mov_id))

    @app.route('/abono/<int:abono_id>/asignar-indirecto', methods=['POST'])
    @login_required
    def asignar_abono_indirecto(abono_id):
        abono_origen = Abono.query.get_or_404(abono_id)
        detalle_origen = abono_origen.detalle
        mov_origen = detalle_origen.movimiento

        pagador_todo = DetalleMovimiento.query.filter_by(movimiento_id=mov_origen.id, pago_todo=True).first()
        if not pagador_todo:
            flash('No hay pagador principal asociado a este movimiento.', 'error')
            return redirect(url_for('movimiento_detail', mov_id=mov_origen.id))

        movimiento_id = request.form.get('movimiento_id')
        monto_str = request.form.get('montoAcum', '0')
        try:
            monto = parse_amount(monto_str)
        except ValueError:
            flash('Monto inválido.', 'error')
            return redirect(url_for('movimiento_detail', mov_id=mov_origen.id))

        monto_total_distribuido = db.session.query(db.func.coalesce(db.func.sum(AbonoIndirecto.monto_aplicado), 0)).filter(AbonoIndirecto.abono_id == abono_id).scalar() or 0
        monto_restante_abono = int(abono_origen.monto) - int(monto_total_distribuido)
        if monto > monto_restante_abono:
            flash(f'El monto supera el saldo disponible del abono ({format_currency_int(monto_restante_abono)}).', 'error')
            return redirect(url_for('movimiento_detail', mov_id=mov_origen.id, abono_id=abono_id))

        if not movimiento_id or movimiento_id.strip() == '' or movimiento_id == '0':
            if monto_restante_abono <= 0:
                flash('No hay monto restante para asignar a saldo a favor.', 'info')
                return redirect(url_for('movimiento_detail', mov_id=mov_origen.id))

            nuevo_saldo = SaldoFavor(persona_id=pagador_todo.persona_id, user_id=current_user.id, monto=monto_restante_abono, fecha=datetime.utcnow(), comentario=f'Saldo a favor generado por abono #{abono_id} del movimiento #{mov_origen.id}')
            db.session.add(nuevo_saldo)
            db.session.commit()

            flash(f'Se registró {format_currency_int(monto_restante_abono)} como saldo a favor para {pagador_todo.person.name}.', 'success')
            return redirect(url_for('movimiento_detail', mov_id=mov_origen.id))

        detalle_destino = DetalleMovimiento.query.filter_by(movimiento_id=movimiento_id, persona_id=pagador_todo.persona_id).first()
        if not detalle_destino:
            flash('No se encontró un registro válido en el movimiento destino.', 'error')
            return redirect(url_for('movimiento_detail', mov_id=mov_origen.id))

        monto_aplicable = min(monto, int(detalle_destino.falta))

        nuevo_abono = Abono(detalle_id=detalle_destino.id, monto=monto_aplicable, fecha=datetime.now())
        db.session.add(nuevo_abono)
        db.session.flush()

        detalle_destino.abonado = int(detalle_destino.abonado) + int(monto_aplicable)
        detalle_destino.falta = max(int(detalle_destino.monto) - int(detalle_destino.abonado), 0)
        detalle_destino.estado = 'Pagado' if detalle_destino.falta == 0 else 'Debe'

        relacion = AbonoIndirecto(abono_id=abono_origen.id, movimiento_destino_id=movimiento_id, persona_destino_id=detalle_destino.persona_id, monto_aplicado=monto_aplicable)
        db.session.add(relacion)
        db.session.commit()

        flash(f'Abono indirecto aplicado correctamente ({format_currency_int(monto_aplicable)}).', 'success')
        return redirect(url_for('movimiento_detail', mov_id=mov_origen.id))

    # SALDO A FAVOR
    @app.route('/saldo-favor', methods=['GET'])
    @login_required
    def saldo_favor():
        personas = Person.query.filter_by(user_id=current_user.id).all()
        data = []
        for p in personas:
            movimientos = SaldoFavor.query.filter_by(persona_id=p.id, user_id=current_user.id).all()
            saldo_total = sum(m.monto if m.tipo == 'ingreso' else -m.monto for m in movimientos)
            ultima_fecha = max((m.fecha for m in movimientos), default=None)
            data.append({'id': p.id, 'name': p.name, 'saldo_total': int(saldo_total), 'ultima_fecha': ultima_fecha})
        return render_template('saldo_favor.html', registros=data, personas=personas)

    @app.route('/saldo-favor/add', methods=['POST'])
    @login_required
    def saldo_favor_add():
        persona_id = request.form.get('persona_id')
        monto_raw = request.form.get('monto', '0')
        comentario = request.form.get('comentario', '').strip()
        fecha_raw = request.form.get('fecha', '').strip()
        tipo = 'ingreso'

        if not persona_id or not monto_raw or not fecha_raw:
            flash('Todos los campos son obligatorios.', 'danger')
            return redirect(url_for('saldo_favor'))

        try:
            monto = parse_amount(monto_raw)
            fecha = datetime.strptime(fecha_raw, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Formato inválido en monto o fecha.', 'danger')
            return redirect(url_for('saldo_favor'))

        if monto < 0:
            tipo = 'egreso'
            monto = abs(monto)

        nuevo = SaldoFavor(persona_id=persona_id, user_id=current_user.id, monto=monto, comentario=comentario, fecha=fecha, tipo=tipo)
        db.session.add(nuevo)
        db.session.commit()
        flash('Saldo registrado correctamente.', 'success')
        return redirect(url_for('saldo_favor'))

    @app.route('/saldo-favor/historico/<int:persona_id>')
    @login_required
    def saldo_favor_historico(persona_id):
        persona = Person.query.filter_by(id=persona_id, user_id=current_user.id).first_or_404()
        registros = SaldoFavor.query.filter_by(persona_id=persona.id, user_id=current_user.id).order_by(SaldoFavor.fecha.desc()).all()
        saldo_total = sum(r.monto if r.tipo == 'ingreso' else -r.monto for r in registros)
        return render_template('saldo_favor_historico.html', persona=persona, registros=registros, saldo_total=int(saldo_total))

    # EXPORT CSV
    @app.route('/export/csv')
    @login_required
    def export_csv():
        movimientos = Movimiento.query.filter_by(user_id=current_user.id).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Fecha', 'Tipo', 'Categoría', 'Descripción', 'Monto'])
        for m in movimientos:
            writer.writerow([m.fecha, m.tipo, m.categoria, m.descripcion, int(m.monto)])
        output.seek(0)
        return send_file(io.BytesIO(output.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='movimientos.csv')

    # EXPORT PDF
    @app.route('/export/pdf')
    @login_required
    def export_pdf():
        movimientos = Movimiento.query.filter_by(user_id=current_user.id).all()
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        pdf.setFont('Helvetica-Bold', 14)
        pdf.drawString(220, height - 50, 'Reporte de Movimientos')
        y = height - 100
        pdf.setFont('Helvetica', 10)
        for m in movimientos:
            pdf.drawString(50, y, f"{m.fecha} | {m.tipo.capitalize()} | {m.categoria} | {format_currency_int(m.monto)}")
            y -= 15
            if y < 50:
                pdf.showPage()
                y = height - 50
        pdf.save()
        buffer.seek(0)
        return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='movimientos.pdf')

    # Error handlers
    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        db.session.rollback()
        logger.exception('Integrity error')
        return render_template('errors/error_general.html'), 409

    @app.errorhandler(401)
    def unauthorized_error(error):
        return render_template('errors/401.html'), 401

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(409)
    def conflict_error(error):
        return render_template('errors/409.html'), 409

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        logger.exception('Internal server error')
        return render_template('errors/500.html'), 500

    # Inicializar base de datos
    with app.app_context():
        db_dir = os.path.join(BASE_DIR, 'db')
        db_file = os.path.join(db_dir, 'database.db')
        if not os.path.exists(db_file):
            os.makedirs(db_dir, exist_ok=True)
            db.create_all()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5226)
