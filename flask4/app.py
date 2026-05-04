from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Модель пользователя
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# класс описывает как выглядит запись поста в базе данных
class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    is_private = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

@login_manager.user_loader # Flask-Login будет вызывать её, когда нужно загрузить пользователя по id из сессии
def load_user(user_id):
    return User.query.get(int(user_id))

# Главная страница
@app.route('/')
def index():
    if current_user.is_authenticated:
        posts = Post.query.order_by(Post.created.desc()).all()
    else:
        posts = Post.query.filter_by(is_private=False).order_by(Post.created.desc()).all()
    return render_template('index.html', posts=posts)

# Просмотр поста
@app.route('/post/<int:id>')
def view_post(id):
    post = Post.query.get_or_404(id)
    if post.is_private and not current_user.is_authenticated:
        flash('Пост приватный', 'error')
        return redirect(url_for('index'))
    return render_template('post.html', post=post)

# Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST': #проверка каким методом пришел запрос
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password): #проверка пароль верный и пользователь найден
            login_user(user)
            flash('Вход выполнен', 'success')
            return redirect(url_for('index'))
        flash('Неверный логин или пароль', 'error')
    return render_template('login.html')

# Выход
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Выход выполнен', 'info')
    return redirect(url_for('index'))

@app.route('/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        post = Post(
            title=request.form.get('title'),
            content=request.form.get('content'),
            is_private=request.form.get('is_private') == 'on',
            author=current_user
        )
        db.session.add(post)
        db.session.commit()
        flash('Пост создан', 'success')
        return redirect(url_for('index'))
    return render_template('edit_post.html', title='Новый пост')
# для редактирования поста
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_post(id):
    post = Post.query.get_or_404(id)
    if post.author != current_user:
        flash('Это не ваш пост', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST': #проверка метода запроса
        post.title = request.form.get('title')
        post.content = request.form.get('content')
        post.is_private = request.form.get('is_private') == 'on'
        db.session.commit()
        flash('Пост обновлён', 'success')
        return redirect(url_for('view_post', id=post.id))

    return render_template('edit_post.html', post=post, title='Редактировать')
# для удаления поста
@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_post(id):
    post = Post.query.get_or_404(id) #ищем пост по id
    if post.author == current_user: #проверка что текущий пользователь автор поста
        db.session.delete(post)
        db.session.commit()
        flash('Пост удалён', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('✅ База данных создана!')
    app.run(debug=True)