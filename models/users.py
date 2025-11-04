from flask_login import UserMixin
from models import db
from datetime import datetime


# ==============================
# Usuario y relaciones
# ==============================
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    # Relaciones
    persons = db.relationship('Person', backref='owner', lazy=True)
    movimientos = db.relationship('Movimiento', backref='owner', lazy=True)
    projects = db.relationship('Project', secondary='project_members', back_populates='members')


# ==============================
# Personas vinculadas al usuario
# ==============================
class Person(db.Model):
    __tablename__ = 'person'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    detalles = db.relationship('DetalleMovimiento', backref='person', lazy=True)


# ==============================
# Proyectos compartidos (multiusuario)
# ==============================
class Project(db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    members = db.relationship('User', secondary='project_members', back_populates='projects')


class ProjectMembers(db.Model):
    __tablename__ = 'project_members'
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)

# ==============================
# Saldos a Favor
# ==============================
class SaldoFavor(db.Model):
    __tablename__ = 'saldo_favor'
    id = db.Column(db.Integer, primary_key=True)
    persona_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    comentario = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    tipo = db.Column(db.String(10), default='ingreso')  # ingreso o egreso

    persona = db.relationship('Person', backref='saldos_favor', lazy=True)
    usuario = db.relationship('User', backref='saldos_favor', lazy=True)
