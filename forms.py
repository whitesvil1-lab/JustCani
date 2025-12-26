from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Regexp

class RegistrationForm(FlaskForm):
    username = StringField('Username', 
        validators=[
            DataRequired(message="Username wajib diisi"),
            Length(min=3, max=20, message="Username 3-20 karakter")
        ])
    
    email = StringField('Alamat email', 
        validators=[
            DataRequired(message="Email wajib diisi"),
            Email(message="Format email tidak valid")
        ])
    
    whatsapp = StringField('Nomor WhatsApp', 
        validators=[
            DataRequired(message="Nomor WhatsApp wajib diisi"),
            Regexp(r'^\+?[0-9]{10,15}$', message="Format nomor tidak valid")
        ])
    
    password = PasswordField('Kata sandi', 
        validators=[
            DataRequired(message="Password wajib diisi"),
            Length(min=6, message="Minimal 6 karakter")
        ])
    
    confirm_password = PasswordField('Konfirmasi kata sandi', 
        validators=[
            DataRequired(message="Konfirmasi password wajib"),
            EqualTo('password', message="Password tidak cocok")
        ])
    
    submit = SubmitField('Daftar')

class LoginForm(FlaskForm):
    # Ubah label menjadi "Email atau Username"
    email = StringField('Email atau Username', 
        validators=[
            DataRequired(message="Email/Username wajib diisi")
            # Hapus Email() validator biar bisa input username
        ])
    
    password = PasswordField('Password', 
        validators=[
            DataRequired(message="Password wajib diisi")
        ])
    
    submit = SubmitField('Login')