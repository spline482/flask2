# импортируем необходимые модули Flask
from flask import Flask, render_template, redirect, url_for, request, flash
# импортируем компоненты Flask-Login для авторизации
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
# импортируем наши формы
from forms import LoginForm, RegisterForm
# импортируем утилиты
from utils import load_users, save_users, hash_password, check_password, get_current_datetime
# импортируем os для работы с путями
import os

app = Flask(__name__)
# устанавливаем секретный ключ для защиты сессий
app.config['SECRET_KEY'] = os.urandom(256)
# настраиваем максимальный размер загружаемых данных (16 МБ)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# инициализируем менеджер авторизации
login_manager = LoginManager()
# привязываем его к нашему приложению
login_manager.init_app(app)
# указываем, на какую страницу перенаправлять неавторизованных пользователей
login_manager.login_view = 'login'

class User(UserMixin):
    # конструктор класса — создаёт объект пользователя
    def __init__(self, user_id, username, password_hash, registered_at, last_login):
        # сохраняем id пользователя
        self.id = user_id
        # сохраняем имя пользователя
        self.username = username
        # сохраняем хеш пароля (не сам пароль!)
        self.password_hash = password_hash
        # сохраняем дату регистрации
        self.registered_at = registered_at
        # сохраняем дату последнего входа
        self.last_login = last_login

# функция, которую Flask-Login вызывает для загрузки пользователя по id
@login_manager.user_loader
def load_user(user_id):
    # загружаем всех пользователей из json-файла
    users = load_users()
    # ищем пользователя с нужным id
    user_data = users.get(str(user_id))
    # если пользователь не найден — возвращаем None
    if not user_data:
        return None
    # создаём и возвращаем объект User с данными из файла
    return User(
        user_id=str(user_id),
        username=user_data['username'],
        password_hash=user_data['password_hash'],
        registered_at=user_data['registered_at'],
        last_login=user_data.get('last_login', 'Никогда')
    )

# маршрут для главной страницы (
@app.route('/')
def index():
    # рендерим шаблон index.html
    return render_template('index.html')

# маршрут для страницы входа (доступен всем)
@app.route('/login', methods=['GET', 'POST'])
def login():
    # если пользователь уже авторизован перенаправляем на главную
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    # создаём объект формы входа
    form = LoginForm()

    # если форма отправлена методом POST и прошла валидацию
    if request.method == 'POST' and form.validate_on_submit():
        # получаем введённые данные
        username = form.username.data
        password = form.password.data
        # загружаем всех пользователей
        users = load_users()
        # перебираем всех пользователей в поисках совпадения
        for user_id, user_data in users.items():
            # проверяем имя и пароль (сравниваем с хешем)
            if user_data['username'] == username and check_password(user_data['password_hash'], password):
                # создаём объект пользователя для Flask-Login
                user_obj = User(
                    user_id=str(user_id),
                    username=username,
                    password_hash=user_data['password_hash'],
                    registered_at=user_data['registered_at'],
                    last_login=get_current_datetime()  # обновляем время входа
                )
                # обновляем last_login в файле данных
                user_data['last_login'] = user_obj.last_login
                save_users(users)
                # авторизуем пользователя в сессии
                login_user(user_obj)
                # показываем сообщение об успешном входе
                flash(f'Добро пожаловать, {username}!', 'success')
                # перенаправляем на главную
                return redirect(url_for('index'))

        # если цикл завершился без нахождения пользователя  ошибка
        flash('Неверное имя пользователя или пароль.', 'error')
    # если метод GET или форма не валидна  показываем форму
    return render_template('login.html', form=form)
# маршрут для выхода из системы для авторизованных
@app.route('/logout')
@login_required  # декоратор запрещает доступ неавторизованным
def logout():
    # получаем имя пользователя для сообщения
    username = current_user.username
    # разлогиниваем пользователя
    logout_user()
    # показываем сообщение
    flash(f'Вы вышли из системы, {username}.', 'info')
    # перенаправляем на главную
    return redirect(url_for('index'))
# маршрут для регистрации нового пользователя
@app.route('/register', methods=['GET', 'POST'])
@login_required  # только авторизованный пользователь может регистрировать других
def register():
    # создаём объект формы регистрации
    form = RegisterForm()
    # если форма отправлена и прошла валидацию
    if request.method == 'POST' and form.validate_on_submit():
        # получаем данные из формы
        new_username = form.username.data
        new_password = form.password.data

        # загружаем текущих пользователей
        users = load_users()

        # генерируем новый id как максимальный существующий + 1
        # если пользователей нет — начинаем с 1
        new_id = str(max((int(uid) for uid in users.keys()), default=0) + 1)

        # создаём запись нового пользователя
        new_user = {
            'username': new_username,  # имя пользователя
            'password_hash': hash_password(new_password),  # хеш пароля
            'registered_at': get_current_datetime(),  # дата регистрации
            'last_login': 'Никогда'  # пока не входил
        }

        # добавляем нового пользователя в словарь по id
        users[new_id] = new_user

        # сохраняем обновлённый список в json-файл
        save_users(users)

        # показываем сообщение об успехе
        flash(f'Пользователь "{new_username}" успешно зарегистрирован!', 'success')

        # перенаправляем на страницу со списком пользователей
        return redirect(url_for('users_list'))

    # если метод GET или форма не валидна — показываем форму
    return render_template('register_admin.html', form=form)
# маршрут для просмотра списка всех пользователей для авторизованных
@app.route('/users')
@login_required
def users_list():
    # загружаем всех пользователей из файла
    users = load_users()
    # рендерим шаблон, передавая словарь пользователей
    return render_template('users_list.html', users=users)

# маршрут для удаления пользователя
@app.route('/delete/<user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    # загружаем пользователей
    users = load_users()

    # проверяем, существует ли пользователь с таким id
    if user_id in users:
        # сохраняем имя для сообщения
        username = users[user_id]['username']
        # удаляем запись из словаря
        del users[user_id]
        # сохраняем изменения в файл
        save_users(users)
        # показываем сообщение
        flash(f'Пользователь "{username}" удалён.', 'success')

    # перенаправляем на список пользователей
    return redirect(url_for('users_list'))

# обработчик ошибки 404
@app.errorhandler(404)
def page_not_found(e):
    # показываем сообщение об ошибке
    flash('Страница не найдена.', 'error')
    # перенаправляем на главную
    return redirect(url_for('index'))

# обработчик ошибки 413 что файл слишком большой
@app.errorhandler(413)
def file_too_large(e):
    flash('Слишком большой запрос.', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    # запускаем сервер в режиме отладки на всех интерфейсах
    app.run(debug=True, host='0.0.0.0', port=5000)
