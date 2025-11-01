from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import date, datetime
from models import db

class Movimiento(db.Model):
    __tablename__ = 'movimiento'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)
    categoria = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.String(300), nullable=True)
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    detalles = db.relationship( 'DetalleMovimiento', backref='movimiento', cascade='all, delete-orphan', lazy=True )

class DetalleMovimiento(db.Model):
    __tablename__ = 'detalle_movimiento'
    id = db.Column(db.Integer, primary_key=True)
    persona_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False)
    movimiento_id = db.Column(db.Integer, db.ForeignKey('movimiento.id'), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    abonado = db.Column(db.Float, nullable=False, default=0)
    falta = db.Column(db.Float, nullable=False, default=0)
    estado = db.Column(db.String(20), nullable=False, default='Debe')
    pago_todo = db.Column(db.Boolean, default=False)

    abonos = db.relationship( 'Abono', backref='detalle', cascade='all, delete-orphan', lazy=True )
class Abono(db.Model):
    __tablename__ = 'abono'
    id = db.Column(db.Integer, primary_key=True)
    detalle_id = db.Column(db.Integer, db.ForeignKey('detalle_movimiento.id'), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    asignaciones_indirectas = db.relationship( 'AbonoIndirecto', back_populates='abono', cascade='all, delete-orphan', lazy=True )

class AbonoIndirecto(db.Model):
    __tablename__ = 'abono_indirecto'
    id = db.Column(db.Integer, primary_key=True)
    abono_id = db.Column(db.Integer, db.ForeignKey('abono.id'), nullable=False)
    movimiento_destino_id = db.Column(db.Integer, db.ForeignKey('movimiento.id'), nullable=False)
    persona_destino_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False)
    monto_aplicado = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    abono = db.relationship('Abono', back_populates='asignaciones_indirectas', lazy=True)
    movimiento_destino = db.relationship( 'Movimiento', backref=db.backref('abonos_indirectos', cascade='all, delete-orphan'), lazy=True )
    persona_destino = db.relationship('Person', lazy=True)
