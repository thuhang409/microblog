from datetime import datetime, timezone
from flask import render_template, flash, redirect, url_for, request
from urllib.parse import urlsplit
from app import app
import sqlalchemy as sa
from app import db
from flask_login import login_user, current_user, logout_user, login_required
from langdetect import detect, LangDetectException
from app.models import User, Post
from app.forms import LoginForm, RegistrationForm, EditProfileForm, EmptyForm, PostForm
from app.translate import translate

@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()


@app.route("/", methods=['GET', 'POST'])
@app.route("/index", methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        try:
            language = detect(form.post.data)
        except LangDetectException:
            language = ''
        post = Post(body=form.post.data, author=current_user, language=language)
        db.session.add(post)
        db.session.commit()
        flash("Your post is now live.")
        return redirect(url_for('index'))
    
    query = current_user.following_posts()
    page = request.args.get('page', 1, type=int) # Get the value of 'page' in URL, with default value is 1, and the value is converted to int
    posts = db.paginate(query, page=page,
                        per_page=app.config['POSTS_PER_PAGE'], error_out=False)
    
    next_url = url_for('index', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) if posts.has_prev else None
    
    return render_template('index.html', title='Home', posts=posts, form=form, next_url=next_url, prev_url=prev_url)

@app.route('/explore')
@login_required
def explore():
    query = sa.select(Post).order_by(Post.timestamp.desc())
    page = request.args.get('page', 1, type=int)
    posts = db.paginate(query, page=page,
                        per_page=app.config['POSTS_PER_PAGE'], error_out=False)
    
    next_url = url_for('explore', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) if posts.has_prev else None
    return render_template('index.html', title='Home', posts=posts, next_url=next_url, prev_url=prev_url) 

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        print(next_page)
        print(urlsplit(next_page))
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')

        # flash(f"Login requested for user {form.username.data}, remember_me={form.remember_me.data}")
        return redirect(next_page)
    return render_template("login.html", title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, language='en')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a user.')
        return redirect(url_for('login'))
    return render_template('register.html', title = "Register", form=form)

@app.route('/user/<username>')
@login_required
def profile(username):
    user = db.first_or_404(sa.select(User).where(User.username==username))
    query = sa.select(Post).where(Post.author==user)
    page = request.args.get('page', 1, type=int) # key default int
    posts = db.paginate(query, page=page, per_page=app.config['POSTS_PER_PAGE'], error_out=False)
    form = EmptyForm()
    next_url = url_for('profile', page=posts.next_num, username=username) if posts.has_next else None
    prev_url = url_for('profile', page=posts.prev_num, username=username) if posts.has_prev else None
    return render_template('profile.html', title='Profile', user=user, posts=posts, form=form, next_url=next_url, prev_url=prev_url)

@app.route('/edit-profile', methods=['GET','POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        print(form.language)
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        current_user.language = form.language.data
        db.session.commit()
        flash("Changed successfully!")
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
        form.language.data = current_user.language
    return render_template('edit_profile.html', title='Edit Profile', form=form)

@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(f'User {username} not found.')
            return redirect(url_for('index'))
        if user == current_user:
            flash('You cannot follow yourself!')
            return redirect(url_for('profile', username=username))
        current_user.follow(user)
        db.session.commit()
        flash(f'You are following {username}!')
        return redirect(url_for('profile', username=username))
    else:
        return redirect(url_for('index'))
    

@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(f'User {username} not found.')
            return redirect(url_for('index'))
        if user == current_user:
            flash('You cannot unfollow yourself!')
            return redirect(url_for('user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(f'You are not following {username}.')
        return redirect(url_for('profile', username=username))
    else:
        return redirect(url_for('index'))
    
@app.route('/translate', methods=['POST'])
@login_required
def translate_text():
    data = request.get_json()
    return {'text': translate(data['text'],
                              data['source_language'],
                              data['dest_language'])}