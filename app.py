import os
from datetime import date, datetime
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models.users import db, User, Person
from models.move import Movimiento, DetalleMovimiento, Abono, AbonoIndirecto
from forms.forms import LoginForm, RegisterForm, PersonForm, MovimientoForm
from flask import send_file
import csv, io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import logging
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from flask import session
from flask_migrate import Migrate


load_dotenv()

logger = logging.getLogger(__name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'db/database.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate = Migrate(app, db) 

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # --- ROUTES ---
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    # Auth: register / login / logout
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        form = RegisterForm()
        if form.validate_on_submit():
            # Verificar si ya existe un usuario con ese nombre
            existing_user = User.query.filter_by(username=form.username.data).first()
            if existing_user:
                flash('El usuario ya existe', 'warning')
                return redirect(url_for('register'))

            # Crear nuevo usuario
            u = User(
                username=form.username.data,
                password=generate_password_hash(form.password.data)
            )
            db.session.add(u)
            db.session.commit()

            # Iniciar sesión automáticamente
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
        movimientos = Movimiento.query.filter_by(user_id=current_user.id).order_by(Movimiento.fecha.desc()).limit(10).all()
        movimientos_saldo = []

        for mov in movimientos:
            total_falta = 0
            for det in mov.detalles:
                abonos_sum = sum(a.monto for a in det.abonos)
                falta_detalle = det.monto - abonos_sum                
                total_falta += falta_detalle
            movimientos_saldo.append({
                'id': mov.id,
                'fecha': mov.fecha,
                'tipo': mov.tipo,
                'categoria': mov.categoria,
                'descripcion': mov.descripcion,
                'monto': mov.monto,
                'falta': total_falta 
            })
        all_movs = Movimiento.query.filter_by(user_id=current_user.id).all()

        ingresos = sum(m.monto for m in all_movs if m.tipo == 'ingreso')
        gastos = sum(m.monto for m in all_movs if m.tipo == 'gasto')
        pagos = sum(m.monto for m in all_movs if m.tipo == 'pago')
        balance = ingresos - gastos

        # Gráfico ingresos vs gastos
        ingresos_gastos_data = {
            "labels": [m.fecha.strftime('%d/%m') for m in all_movs],
            "ingresos": [m.monto for m in all_movs if m.tipo == 'ingreso'],
            "gastos": [m.monto for m in all_movs if m.tipo == 'gasto']
        }

        # Gráfico de categorías
        categorias = {}
        for m in all_movs:
            if m.tipo == 'gasto':
                categorias[m.categoria] = categorias.get(m.categoria, 0) + m.monto

        categorias_data = {
            "labels": list(categorias.keys()),
            "valores": list(categorias.values())
        }

        # Deudas por persona
        persons = Person.query.filter_by(user_id=current_user.id).all()
        deudas = []
        total_deuda = 0

        for p in persons:
            total_monto = 0
            total_abonos = 0
            total_le_deben = 0
            balance = 0
            for d in p.detalles:
                # Solo contar movimientos del usuario logueado
                if d.movimiento.user_id != current_user.id:
                    continue

                # Monto total y abonos personales
                abonos_sum = sum(a.monto for a in d.abonos)
                total_monto += d.monto
                total_abonos += abonos_sum

                # Si esta persona pagó todo el movimiento
                if getattr(d, 'pago_todo', False):
                    otros_detalles = DetalleMovimiento.query.filter(
                        DetalleMovimiento.movimiento_id == d.movimiento_id,
                        DetalleMovimiento.persona_id != p.id
                    ).all()

                    # Sumar la parte que le deben al usuario actual
                    for od in otros_detalles:
                        abonos_od = sum(a.monto for a in od.abonos)
                        deuda_od = max(od.monto - abonos_od, 0)
                        total_le_deben += deuda_od                        

            total_debe = max(total_monto - total_abonos, 0)
            balance = total_debe - total_le_deben
            total_deuda += total_debe

            deudas.append({
                'person': p,
                'debe': total_debe,
                'pagado': total_abonos,
                'le_deben': total_le_deben,
                'balance': balance
            })

        return render_template(
            'dashboard.html',
            movimientos=movimientos_saldo,
            ingresos=ingresos,
            gastos=gastos,
            pagos=pagos,
            balance=balance,
            deudas=deudas,
            ingresos_gastos_data=ingresos_gastos_data,
            categorias_data=categorias_data,
            total_deuda = total_deuda
        )

    @app.template_filter('currency')
    def currency_format(value):
        return "${:,.2f}".format(value or 0)
    
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

        # Verificar si la persona tiene relaciones
        tiene_detalles = bool(p.detalles)
        tiene_abonos = any(d.abonos for d in p.detalles)

        if tiene_detalles or tiene_abonos:
            flash('No puedes eliminar esta persona porque tiene registros asociados a movimientos o abonos.', 'danger')
            return redirect(url_for('personas'))

        db.session.delete(p)
        db.session.commit()
        flash('Persona eliminada correctamente.', 'success')
        return redirect(url_for('personas'))

    @app.route('/movimientos', methods=['GET', 'POST'])
    @login_required
    def movimientos():
        form = MovimientoForm()
        persons = Person.query.filter_by(user_id=current_user.id).all()

        # Filtros por fecha
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
                # Extraer datos del formulario principal
                tipo = request.form.get('tipo', '').strip()
                categoria = request.form.get('categoria', '').strip()
                descripcion = request.form.get('descripcion', '').strip()
                monto_raw = request.form.get('monto', '0').replace(',', '').strip()
                fecha_raw = request.form.get('fecha', '').strip()

                if not tipo or not categoria or not monto_raw or not fecha_raw:
                    flash("Por favor completa todos los campos obligatorios.", "danger")
                    return render_template(
                        'movimientos.html',
                        form=form,
                        movimientos=movimientos_list,
                        persons=persons,
                        desde=desde or '',
                        hasta=hasta or ''
                    )

                monto = float(monto_raw)
                fecha = datetime.strptime(fecha_raw, '%Y-%m-%d').date()

                # Crear movimiento principal
                movimiento = Movimiento(
                    tipo=tipo,
                    categoria=categoria,
                    descripcion=descripcion,
                    monto=monto,
                    fecha=fecha,
                    user_id=current_user.id
                )
                db.session.add(movimiento)
                db.session.flush()  # Obtiene el id sin hacer commit aún

                # Guardar detalles por persona
                for p in persons:
                    key_m = f"monto_{p.id}"
                    key_a = f"abonado_{p.id}"
                    key_e = f"estado_{p.id}"

                    monto_persona_raw = request.form.get(key_m, '').replace(',', '').strip()
                    if not monto_persona_raw:
                        continue  # Saltar si no se ingresó monto para esta persona

                    try:
                        monto_persona = float(monto_persona_raw)
                        abonado = float(request.form.get(key_a, '0').replace(',', '').strip() or 0)
                        falta = max(monto_persona - abonado, 0)
                        estado = request.form.get(key_e, 'Debe')
                        pago_key = f"pago_{p.id}"
                        detalle = DetalleMovimiento(
                            persona_id=p.id,
                            movimiento_id=movimiento.id,
                            monto=monto_persona,
                            abonado=0,  # Inicialmente en 0
                            falta=monto_persona,  # Total adeudado
                            estado=estado
                        )
                        detalle.pago_todo = request.form.get(pago_key) == '1'
                        db.session.add(detalle)
                        db.session.flush()

                        if abonado > 0:
                            abono_inicial = Abono(
                                detalle_id=detalle.id,
                                monto=abonado,
                                fecha=datetime.combine(fecha, datetime.min.time())
                            )
                            db.session.add(abono_inicial)
                            db.session.flush()

                        total_abonos = sum(a.monto for a in detalle.abonos)
                        detalle.abonado = total_abonos
                        detalle.falta = max(detalle.monto - total_abonos, 0)
                        detalle.estado = 'Pagado' if detalle.falta == 0 else 'Debe'

                        db.session.commit()
                    except ValueError as ve:
                        logger.warning(f"Error parseando monto/abonado para {p.name}: {ve}")
                        continue

                db.session.commit()
                flash("Movimiento creado correctamente.", "success")
                return redirect(url_for('movimientos'))

            except Exception as e:
                db.session.rollback()
                logger.error(f"Error guardando movimiento: {e}")
                flash(f"Error al guardar movimiento: {e}", "danger")

        return render_template(
            'movimientos.html',
            form=form,
            movimientos=movimientos_list,
            persons=persons,
            desde=desde or '',
            hasta=hasta or ''
        )

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
                    abonado_total = d.abonado + sum(a.monto for a in d.abonos)
                    deuda_total += max(d.monto - abonado_total, 0)

        if abono_id:
            abono = Abono.query.get(abono_id)
            if abono:
                session['ultimo_abono_monto'] = float(abono.monto)

            if pagador_todo:
                movimientos_deudor = [
                    {
                        "movimiento_id": d.movimiento_id,
                        "categoria": m.categoria,
                        "descripcion": m.descripcion,
                        "falta": float(d.falta)
                    }
                    for d, m in db.session.query(DetalleMovimiento, Movimiento)
                        .filter(
                            DetalleMovimiento.persona_id == pagador_todo.persona_id,
                            DetalleMovimiento.falta > 0,
                            DetalleMovimiento.movimiento_id == Movimiento.id
                        )
                ]

        return render_template(
            'deuda_detalle.html',
            mov=m,
            pagador_todo=pagador_todo,
            deuda_total=deuda_total,
            abono=abono,
            movimientos_deudor=movimientos_deudor,
            abono_monto=session.get('ultimo_abono_monto')
        )

    @app.route('/movimiento/delete/<int:mov_id>', methods=['POST'])
    @login_required
    def movimiento_delete(mov_id):
        movimiento = Movimiento.query.filter_by(id=mov_id, user_id=current_user.id).first_or_404()

        # Solo necesitas eliminar el movimiento; el cascade hará el resto
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
        monto_str = request.form.get('monto', '0').replace(',', '').strip()
        fecha_str = request.form.get('fecha', '').strip()

        try:
            monto = float(monto_str)
            fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%dT%H:%M")
        except ValueError:
            flash('Datos inválidos. Revisa el monto y la fecha.', 'error')
            return redirect(url_for('movimiento_detail', mov_id=mov_id))

        detalle = DetalleMovimiento.query.filter_by(id=detalle_id, movimiento_id=mov.id).first_or_404()

        # Crear el nuevo abono
        nuevo_abono = Abono(detalle_id=detalle.id, monto=monto, fecha=fecha_obj)
        db.session.add(nuevo_abono)
        db.session.flush()

        # Recalcular el total abonado
        total_abonos = sum(a.monto for a in detalle.abonos)
        detalle.abonado = total_abonos
        detalle.falta = max(detalle.monto - total_abonos, 0)
        detalle.estado = 'Pagado' if detalle.falta == 0 else 'Debe'

        db.session.commit()

        flash(f'Abono de ${monto:,.2f} registrado correctamente.', 'success')

        return redirect(url_for('movimiento_detail', mov_id=mov.id, abono_id=nuevo_abono.id))

    @app.route('/abono/<int:abono_id>/delete', methods=['POST'])
    @login_required
    def delete_abono(abono_id):
        abono = Abono.query.get_or_404(abono_id)
        detalle = abono.detalle
        mov_id = detalle.movimiento_id

        # Eliminar abonos indirectos relacionados
        if hasattr(abono, 'indirectos'):  # si existe la relación
            for indirecto in abono.indirectos:
                db.session.delete(indirecto)

        # Restar el monto del abono eliminado
        detalle.abonado -= abono.monto
        if detalle.abonado < 0:
            detalle.abonado = 0

        # Actualizar el estado del detalle
        detalle.estado = 'Pagado' if detalle.abonado >= detalle.monto else 'Debe'

        # Finalmente eliminamos el abono
        db.session.delete(abono)
        db.session.commit()

        flash('Abono y sus relaciones eliminados correctamente.', 'success')
        return redirect(url_for('movimiento_detail', mov_id=mov_id))

    
    @app.route('/abono/<int:abono_id>/asignar-indirecto', methods=['POST'])
    @login_required
    def asignar_abono_indirecto(abono_id):
        abono_origen = Abono.query.get_or_404(abono_id)
        detalle_origen = abono_origen.detalle
        mov_origen = detalle_origen.movimiento

        # Buscar quién pagó todo en el movimiento origen
        pagador_todo = DetalleMovimiento.query.filter_by(
            movimiento_id=mov_origen.id,
            pago_todo=True
        ).first()

        if not pagador_todo:
            flash('No hay pagador principal asociado a este movimiento.', 'error')
            return redirect(url_for('movimiento_detail', mov_id=mov_origen.id))

        # Validar movimiento destino
        movimiento_id = request.form.get('movimiento_id')
        monto_str = request.form.get('montoAcum', '0').replace(',', '').strip()
        try:
            monto = float(monto_str)
        except ValueError:
            flash('Monto inválido.', 'error')
            return redirect(url_for('movimiento_detail', mov_id=mov_origen.id))

        # 🔒 No permitir monto mayor al abono original
        monto_total_distribuido = db.session.query(
            db.func.sum(AbonoIndirecto.monto_aplicado)
        ).filter(AbonoIndirecto.abono_id == abono_id).scalar() or 0

        monto_restante_abono = abono_origen.monto - monto_total_distribuido
        if monto > monto_restante_abono:
            flash(f'El monto supera el saldo disponible del abono (${monto_restante_abono:,.2f}).', 'error')
            return redirect(url_for('movimiento_detail', mov_id=mov_origen.id, abono_id=abono_id))

        # Validar destino
        detalle_destino = DetalleMovimiento.query.filter_by(
            movimiento_id=movimiento_id,
            persona_id=pagador_todo.persona_id
        ).first()

        if not detalle_destino:
            flash('No se encontró un registro válido en el movimiento destino.', 'error')
            return redirect(url_for('movimiento_detail', mov_id=mov_origen.id))

        # Calcular cuánto se puede aplicar sin pasarse del faltante
        monto_aplicable = min(monto, detalle_destino.falta)

        # Crear nuevo abono directo en el movimiento destino
        nuevo_abono = Abono(
            detalle_id=detalle_destino.id,
            monto=monto_aplicable,
            fecha=datetime.now()
        )
        db.session.add(nuevo_abono)
        db.session.flush()

        # Actualizar totales del movimiento destino
        detalle_destino.abonado += monto_aplicable
        detalle_destino.falta = max(detalle_destino.monto - detalle_destino.abonado, 0)
        detalle_destino.estado = 'Pagado' if detalle_destino.falta == 0 else 'Debe'

        # Registrar la relación indirecta
        relacion = AbonoIndirecto(
            abono_id=abono_origen.id,
            movimiento_destino_id=movimiento_id,
            persona_destino_id=detalle_destino.persona_id,
            monto_aplicado=monto_aplicable
        )
        db.session.add(relacion)
        db.session.commit()

        flash(f'Abono indirecto aplicado correctamente (${monto_aplicable:,.2f}).', 'success')
        return redirect(url_for('movimiento_detail', mov_id=mov_origen.id))

    # -------------------------------
    # EXPORTAR A CSV
    # -------------------------------
    @app.route('/export/csv')
    @login_required
    def export_csv():
        movimientos = Movimiento.query.filter_by(user_id=current_user.id).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Fecha', 'Tipo', 'Categoría', 'Descripción', 'Monto'])

        for m in movimientos:
            writer.writerow([m.fecha, m.tipo, m.categoria, m.descripcion, m.monto])

        output.seek(0)
        return send_file(io.BytesIO(output.getvalue().encode('utf-8')),
                        mimetype='text/csv',
                        as_attachment=True,
                        download_name='movimientos.csv')

    # -------------------------------
    # EXPORTAR A PDF
    # -------------------------------
    @app.route('/export/pdf')
    @login_required
    def export_pdf():
        movimientos = Movimiento.query.filter_by(user_id=current_user.id).all()

        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(220, height - 50, "Reporte de Movimientos")

        y = height - 100
        pdf.setFont("Helvetica", 10)
        for m in movimientos:
            pdf.drawString(50, y, f"{m.fecha} | {m.tipo.capitalize()} | {m.categoria} | ${m.monto:.2f}")
            y -= 15
            if y < 50:
                pdf.showPage()
                y = height - 50

        pdf.save()
        buffer.seek(0)
        return send_file(buffer,
                        mimetype='application/pdf',
                        as_attachment=True,
                        download_name='movimientos.pdf')

    # --------------------------
    # Error handlers personalizados
    # --------------------------
    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        db.session.rollback()
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
        return render_template('errors/500.html'), 500

    # Inicializar base de datos al iniciar la app
    with app.app_context():
        if not os.path.exists(os.path.join(BASE_DIR, 'db/database.db')):
                os.makedirs(os.path.join(BASE_DIR, 'db'), exist_ok=True)
                db.create_all()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5226)
