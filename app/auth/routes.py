from datetime import datetime, timezone
from flask import render_template, flash, redirect, url_for, request
from urllib.parse import urlsplit
from app.auth import bp
import sqlalchemy as sa
from app import db
from flask_login import login_user, current_user, logout_user, login_required
from app.models import User
from app.auth.forms import LoginForm, RegistrationForm


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        print(next_page)
        print(urlsplit(next_page))
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('main.index')

        # flash(f"Login requested for user {form.username.data}, remember_me={form.remember_me.data}")
        return redirect(next_page)
    return render_template("auth/login.html", title='Sign In', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, language='en')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a user.')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title = "Register", form=form)
