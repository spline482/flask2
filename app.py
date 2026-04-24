import os
import uuid
import json
import hashlib
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
import mimetypes

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# Конфигурация
UPLOAD_FOLDER = 'uploads'
DB_FILE = 'files_db.json'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'rar'}
FORBIDDEN_EXTENSIONS = {'exe', 'sh', 'php', 'js', 'bat', 'cmd', 'com', 'scr', 'pif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Создаем папку для загрузок если не существует
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def load_files_db():
    """Загружаем базу данных файлов из JSON"""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []


def save_files_db(files_data):
    """Сохраняем базу данных файлов в JSON"""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(files_data, f, indent=2, ensure_ascii=False)


def allowed_file(filename):
    """Проверяем разрешен ли тип файла"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in ALLOWED_EXTENSIONS and ext not in FORBIDDEN_EXTENSIONS


def is_forbidden_extension(filename):
    """Проверяем запрещенные расширения"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in FORBIDDEN_EXTENSIONS


def calculate_md5(filepath):
    """Вычисляем MD5 хэш файла"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_file_extension(filename):
    """Получаем расширение файла"""
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''


def get_subfolder_path(uuid_filename):
    """Создаем путь к подпапке (первые 2 символа / следующие 2 символа)"""
    return os.path.join(UPLOAD_FOLDER, uuid_filename[:2], uuid_filename[2:4])


@app.route('/')
def index():
    """Главная страница - форма загрузки"""
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Обработка загрузки файла"""
    # Проверяем наличие файла в запросе
    if 'file' not in request.files:
        flash('Файл не выбран!', 'error')
        return redirect(url_for('index'))

    file = request.files['file']

    if file.filename == '':
        flash('Файл не выбран!', 'error')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        # Проверяем запрещенные расширения
        if is_forbidden_extension(file.filename):
            flash('Загрузка файлов этого типа запрещена!', 'error')
            return redirect(url_for('index'))

        # Сохраняем оригинальное имя файла
        original_filename = secure_filename(file.filename)
        extension = get_file_extension(original_filename)

        # Генерируем UUID для имени файла
        uuid_filename = f"{uuid.uuid4().hex}.{extension}"

        # Создаем путь с подпапками
        subfolder_path = get_subfolder_path(uuid_filename)
        os.makedirs(subfolder_path, exist_ok=True)

        # Полный путь к файлу
        file_path = os.path.join(subfolder_path, uuid_filename)

        # Проверяем на дубликат по MD5 хэшу
        file_content = file.read()
        file_md5 = hashlib.md5(file_content).hexdigest()

        # Загружаем базу данных
        files_data = load_files_db()

        # Проверяем是否存在 дубликат
        for saved_file in files_data:
            if saved_file.get('md5') == file_md5:
                flash(
                    f'Файл уже был загружен! Оригинал: {saved_file["original_name"]}, Дата: {saved_file["upload_date"]}',
                    'warning')
                return redirect(url_for('index'))

        # Сохраняем файл
        file.seek(0)  # Возвращаем указатель в начало
        file.save(file_path)

        # Получаем относительный путь для отображения
        relative_path = os.path.relpath(file_path, start='.')

        # Добавляем информацию о файле в базу
        file_info = {
            'uuid_name': uuid_filename,
            'original_name': original_filename,
            'md5': file_md5,
            'extension': extension,
            'upload_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'file_path': relative_path,
            'size': os.path.getsize(file_path)
        }

        files_data.append(file_info)
        save_files_db(files_data)

        flash(f'Файл "{original_filename}" успешно загружен!', 'success')
        return redirect(url_for('view_files'))

    else:
        flash('Недопустимый тип файла!', 'error')
        return redirect(url_for('index'))


@app.route('/files')
def view_files():
    """Просмотр списка загруженных файлов"""
    files_data = load_files_db()
    return render_template('files_list.html', files=files_data)


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Отдача загруженного файла"""
    return send_from_directory('.', filename)


@app.route('/delete/<int:index>', methods=['POST'])
def delete_file(index):
    """Удаление файла"""
    files_data = load_files_db()

    if 0 <= index < len(files_data):
        file_info = files_data[index]
        file_path = file_info['file_path']

        # Удаляем файл с диска
        if os.path.exists(file_path):
            os.remove(file_path)

        # Удаляем пустые папки
        folder_path = os.path.dirname(file_path)
        if os.path.exists(folder_path) and not os.listdir(folder_path):
            os.rmdir(folder_path)
            parent_folder = os.path.dirname(folder_path)
            if os.path.exists(parent_folder) and not os.listdir(parent_folder):
                os.rmdir(parent_folder)

        # Удаляем из базы
        files_data.pop(index)
        save_files_db(files_data)

        flash(f'Файл "{file_info["original_name"]}" удален!', 'success')

    return redirect(url_for('view_files'))


@app.errorhandler(413)
def too_large(e):
    """Обработка ошибки слишком большого файла"""
    flash('Файл слишком большой! Максимальный размер: 16MB', 'error')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
