from app import app, db, User

# Создаём базу данных и первого пользователя
with app.app_context():
    # Сначала создаём таблицы
    db.create_all()
    print('✅ Таблицы созданы!')

    # Проверяем, есть ли уже пользователь
    if not User.query.filter_by(username='admin').first():
        user = User(username='admin')
        user.set_password('admin123')
        db.session.add(user)
        db.session.commit()
        print('Пользователь "admin" создан! Пароль: admin123')
    else:
        print('Пользователь "admin" уже существует!')