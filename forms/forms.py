from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, SelectField, DateField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, InputRequired

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class RegisterForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired(), Length(min=3)])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=4)])
    submit = SubmitField('Registrar')

class PersonForm(FlaskForm):
    name = StringField('Nombre', validators=[DataRequired(), Length(min=1)])
    submit = SubmitField('Agregar')

class MovimientoForm(FlaskForm):
    tipo = SelectField('Tipo', choices=[('ingreso', 'Ingreso'), ('gasto', 'Gasto'), ('pago', 'Pago')], validators=[InputRequired()])
    categoria = StringField('Categoría', validators=[DataRequired()])
    descripcion = TextAreaField('Descripción')
    monto = FloatField('Monto total', validators=[DataRequired()])
    fecha = DateField('Fecha', validators=[DataRequired()])
    submit = SubmitField('Guardar')
