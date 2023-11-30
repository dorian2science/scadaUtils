from flask import Flask, render_template, request, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this to a secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gaia.db'  # Use SQLite or your preferred database
db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

class Book(db.Model):
    __tablename__ = 'books'  # Specify the table name explicitly if needed
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    publication_year = db.Column(db.Integer)
    isbn = db.Column(db.String(13), unique=True)
    description = db.Column(db.Text)

    def __init__(self, title, author, publication_year=None, isbn=None, description=None):
        self.title = title
        self.author = author
        self.publication_year = publication_year
        self.isbn = isbn
        self.description = description

    def __repr__(self):
        return f'<Book {self.title} by {self.author}>'

class User(UserMixin, db.Model):
    __tablename__ = 'users'  # Specify the table name explicitly if it's different from the default
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    surname = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    surname = StringField('Surname', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    where_from = StringField('How did you hear about the website', validators=[DataRequired()])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = StringField('email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log in')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def register_user():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if the email is already registered
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user is None:
            # Create a new user and add to the database
            new_user = User(
                name=form.name.data,
                surname=form.surname.data,
                email=form.email.data,
                password=form.password.data
            )
            db.session.add(new_user)
            db.session.commit()
            # flash('Account created successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Email address is already registered. Please use a different email.', 'danger')
    return render_template('register.html', form=form)

def user_login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))  # Redirect to the dashboard if already logged in
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.password == form.password.data:
        # if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            # flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))  # Redirect to the dashboard if already logged in
        else:
            flash('Invalid email or password. Please try again.', 'danger')
    return render_template('login.html', form=form)
