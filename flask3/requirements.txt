from utils import hash_password

# Генерируем хеш для пароля 'admin123'
hashed = hash_password('admin123')
print(f"Хеш пароля: {hashed}")