# импортируем базовый класс формы из Flask-WTF
from flask_wtf import FlaskForm
# импортируем поля для ввода текста и пароля
from wtforms import StringField, PasswordField, SubmitField
# импортируем валидаторы для проверки данных
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
# импортируем модуль string для работы с символами
import string
# импортируем наши утилиты
from utils import load_users


# форма для входа в систему
class LoginForm(FlaskForm):
    # поле для имени пользователя
    username = StringField('Имя пользователя', validators=[DataRequired()])
    # поле для пароля
    password = PasswordField('Пароль', validators=[DataRequired()])
    # кнопка отправки формы
    submit = SubmitField('Войти')


# форма для регистрации нового пользователя
class RegisterForm(FlaskForm):

    # валидатор для проверки сложности пароля
    def validate_password_strength(self, field):
        # получаем введённый пароль
        password = field.data
        # проверяем минимальную длину
        if len(password) < 8:
            # если пароль короткий — выбрасываем ошибку
            raise ValidationError('Пароль должен быть не короче 8 символов.')
        # проверяем наличие хотя бы одной цифры
        if not any(c.isdigit() for c in password):
            raise ValidationError('Пароль должен содержать хотя бы одну цифру.')
        # проверяем наличие хотя бы одной строчной буквы
        if not any(c.islower() for c in password):
            raise ValidationError('Пароль должен содержать хотя бы одну строчную букву.')
        # проверяем наличие хотя бы одной заглавной буквы
        if not any(c.isupper() for c in password):
            raise ValidationError('Пароль должен содержать хотя бы одну заглавную букву.')
        # проверяем наличие хотя бы одного специального символа
        if not any(c in string.punctuation for c in password):
            raise ValidationError('Пароль должен содержать хотя бы один спецсимвол (!@#$%^&*).')

    # валидатор для проверки уникальности имени пользователя
    def validate_username_unique(self, field):
        # получаем введённое имя
        username = field.data
        # загружаем всех пользователей из файла
        users = load_users()
        # перебираем всех пользователей
        for user_id, user_data in users.items():
            # если имя уже занято — выбрасываем ошибку
            if user_data['username'] == username:
                raise ValidationError('Пользователь с таким именем уже существует.')
        # проверяем запрещённые имена
        if username.lower() in ['admin', 'root', 'superuser', 'administrator']:
            raise ValidationError('Это имя пользователя запрещено к использованию.')
        # проверяем допустимые символы
        if not all(c in string.ascii_lowercase + string.ascii_uppercase + string.digits + '_' for c in username):
            raise ValidationError('Имя может содержать только латинские буквы, цифры и подчёркивание.')

    # поле для имени пользователя с валидаторами
    username = StringField('Имя пользователя', validators=[
        DataRequired(message='Имя пользователя обязательно.'),
        Length(min=4, max=25, message='Имя должно быть от 4 до 25 символов.'),
        validate_username_unique
    ])

    # поле для пароля с валидаторами
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Пароль обязателен.'),
        Length(min=8, message='Пароль должен быть не короче 8 символов.'),
        validate_password_strength #проверка сложности
    ])

    # поле для подтверждения пароля
    confirm = PasswordField('Подтвердите пароль', validators=[
        DataRequired(message='Подтверждение пароля обязательно.'),
        EqualTo('password', message='Пароли должны совпадать.')  # сравниваем с полем password
    ])

    # кнопка отправки формы
    submit = SubmitField('Зарегистрировать')