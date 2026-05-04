
import sys  # Системные параметры
import io  # Работа с потоками ввода вывода в памяти
import contextlib  # Контекстные менеджеры, нужен для redirect_stdout
from itertools import cycle  # Бесконечный итератор для циклического перебора статусов/приоритетов
import datetime  # дата и время
from flask import Flask, jsonify, request  # основные компоненты Flask: приложение, JSON-ответы, запросы


#допустимые статусы задачи для валидации
status_lst = ["cancelled", "completed", "in_progress", "pending"]
#допустимые приоритеты задачи
priority_lst = ["high", "low", "medium"]



#функция генерации начальных данных
def get_task_list():

    #cоздаём виртуальный файл в памяти для перехвата вывода print()
    f = io.StringIO()

    #перенаправляем стандартный вывод (print) в наш виртуальный файл
    with contextlib.redirect_stdout(f):
        import this

    #получаем весь перехваченный текст как строку
    text = f.getvalue()

    #создаём бесконечные циклы для статусов и приоритетов
    status_cycle = cycle(status_lst)
    priority_cycle = cycle(priority_lst)

    tasks_lst = []  #итоговый список задач
    num = 0  #счётчик для генерации уникальных ID

    # Проходим по каждой строке текста
    for line in text.splitlines():
        # Пропускаем пустые строки
        if not line:
            continue

        num += 1 #увеличиваем счётчик (это будет ID задачи)

        # словарь-задачу со всеми требуемыми полями
        tasks_lst.append(
            {
            "id": num, #уникальный числовой идентификатор
            "title": "Zen of Python", #общий заголовок для всех задач
            "description": line,  #текст строки из философии Python
            "status": next(status_cycle),  #берём следующий статус из цикла
            "priority": next(priority_cycle),  #берём следующий приоритет из цикла
            "created_at": datetime.datetime.now().isoformat(),  #текущее время в формате ISO 8601
            "updated_at": datetime.datetime.now().isoformat(),  #время последнего обновления
            "deleted_at": None, #поле для soft delete (пока задача не удалена)
        })

        return tasks_lst #возврат готового списка задач


# ИНИЦИАЛИЗАЦИЯ ДАННЫХ ПРИ ЗАПУСКЕ ПРИЛОЖЕНИЯ

tasks_lst = get_task_list()#вызов функции и сохранение результата в глобальную переменную

app = Flask(__name__)  # Создаём экземпляр Flask-приложения



#главная страница с документацией
@app.route("/")#Маршрут для корневого URL: http://127.0.0.1:5000/
def index():
    """Возвращает JSON с описанием API для удобства тестирования"""
    return jsonify({
        "service": "Task Management API",#Название сервиса
        "version": "v1",#Версия API
        "base_url": "/api/v1/tasks",#путь
        "endpoints": { #список доступных методов
            "GET /api/v1/tasks": "Получить список задач (параметры: query, order, offset)",
            "GET /api/v1/tasks/<id>": "Получить задачу по ID",
            "POST /api/v1/tasks": "Создать новую задачу (JSON: title, description, status, priority)",
            "PATCH /api/v1/tasks/<id>": "Частично обновить задачу",
            "DELETE /api/v1/tasks/<id>": 'Удалить задачу (soft delete, status="cancelled")'
        },
        "example_requests": [  # URL для быстрого тестирования
            "http://127.0.0.1:5000/api/v1/tasks", #показывает все задачи
            "http://127.0.0.1:5000/api/v1/tasks/1",#показывает одну задачу
            "http://127.0.0.1:5000/api/v1/tasks?query=never&order=-id" #поиск
        ]
    })

#поиск задачи по id
def find_task(task_id):
    """
    Ищет задачу в списке tasks_lst по её идентификатору.
    Возвращает словарь-задачу или None, если не найдено.
    """
    try:
        #преобразовать ID из строки (из URL) в целое число
        tid = int(task_id)
    except ValueError:
        #если преобразование не удалось — задача не найдена
        return None

    #перебираем все задачи в списке
    for task in tasks_lst:
        #сравниваем ID задачи с искомым
        if task["id"] == tid:
            return task #нашли — возвращаем задачу

    # Если цикл завершился без возврата — задача не найдена
    return None

# получить список задач (GET /api/v1/tasks)
@app.route("/api/v1/tasks", methods=["GET"])
def get_tasks_lst():
    """
    Возвращает отфильтрованный, отсортированный и пагинированный список задач.
    Поддерживает параметры: query (поиск), order (сортировка), offset (смещение).
    """
    #получаем параметры из строки запроса
    query = request.args.get("query", "").lower()  # Поисковый запрос и приводим к нижнему регистру
    order = request.args.get("order", "id")  #поле для сортировки
    offset = int(request.args.get("offset", 0))  # Смещение для пагинации, по умолчанию 0

    #фильтрация по поисковому запросу
    if query:#если пользователь ввёл поисковый запрос
        # Оставляем только задачи, где запрос есть в title ИЛИ description (регистронезависимо)
        filtered = [t for t in tasks_lst if query in t["title"].lower() or query in t["description"].lower()]
    else:  # Если запроса нет — берём все задачи
        filtered = list(tasks_lst)  #копируем список, чтобы не менять оригинал

#сортировка
    reverse = False  # сортировать по убыванию
    sort_key = order  # Имя поля, по которому сортируем

    #проверка , есть ли префикс "-" для сортировки по убыванию (например, "-id")
    if order.startswith("-"):
        reverse = True  #включить обратный порядок
        sort_key = order[1:]#Убрать "-" из имени поля

    #если поле сортировки пустое используем "id" по умолчанию
    sort_key = sort_key or "id"

    #безопасная функция сортировки
    def safe_sort_key(item):
        """
        Возвращает ключ для сортировки, обрабатывая None и разные типы данных.
        Кортеж (val is not None, val) гарантирует, что None всегда будут в конце.
        """
        val = item.get(sort_key) #Получаем значение поля из задачи
        # Если значение None — заменяем на пустую строку для безопасного сравнения
        return (val is not None, val if val is not None else "")

    #сортировка списка с использованием нашей безопасной функции
    filtered.sort(key=safe_sort_key, reverse=reverse)

    #пагинация и ограничение
    #возвращает срез списка: начиная с offset, не более 10 элементов
    return jsonify({"tasks": filtered[offset:offset + 10]})

# получить одну задачу (GET /api/v1/tasks/<task_id>)
@app.route("/api/v1/tasks/<task_id>", methods=["GET"])
def get_task(task_id):
    """
    Возвращает задачу по её уникальному ID.
    Если задача не найдена — возвращает ошибку 404.
    """
    task = find_task(task_id)# ищем задачу с помощью вспомогательной функции

    # Если задача не найдена — возвращаем JSON с ошибкой и статусом 404
    if task is None:
        return jsonify({"error": "Задача не найдена"}), 404

    # Если найдена возвращаем задачу в формате JSON
    return jsonify(task)

# создать новую задачу (POST /api/v1/tasks)
@app.route("/api/v1/tasks", methods=["POST"])
def post_tasks():
    """
    Создаёт новую задачу на основе данных из тела запроса (JSON).
    Выполняет валидацию обязательных полей и допустимых значений.
    """
    #получить JSON из тела запроса; silent=True предотвращает исключение при ошибке
    data = request.get_json(silent=True)

    # Если JSON не передан или он пустой возвращаем ошибку
    if not data:
        return jsonify({"error": "Отсутствуют данные JSON"}), 400

    # валидация обязательных полей
    if "title" not in data:  # Проверка наличия заголовка
        return jsonify({"error": "Пропущен обязательный параметр `title`"}), 400
    if "description" not in data:  # Проверка наличия описания
        return jsonify({"error": "Пропущен обязательный параметр `description`"}), 400

    # обработка опциональных полей со значениями по умолчанию
    status = data.get("status", "pending")  #если status не указан — используем "pending"
    priority = data.get("priority", "medium")  #если priority не указан — используем "medium"

    #валидация допустимых значений
    if status not in status_lst:  #проверка, что статус из разрешённого списка
        return jsonify({"error": "Поле `status` невалидно"}), 400
    if priority not in priority_lst:  #проверка, что приоритет из разрешённого списка
        return jsonify({"error": "Поле `priority` невалидно"}), 400

    #создание новой задачи
    now = datetime.datetime.now().isoformat()#текущее время
    new_task = {
        "id": len(tasks_lst) + 1,  # Новый ID = текущее количество задач + 1
        "title": data["title"],  # Заголовок из запроса
        "description": data["description"],  # Описание из запроса
        "status": status,  #статус
        "priority": priority,  #приоритет
        "created_at": now,  #время создания
        "updated_at": now,  #время последнего обновления (совпадает с созданием)
        "deleted_at": None  #задача ещё не удалена
    }

    tasks_lst.append(new_task)#добавляем новую задачу в глобальный список

    return jsonify(new_task), 200 #возвращает созданную задачу с кодом 200 (успешно)

#удаление задачи (SOFT DELETE) (DELETE /api/v1/tasks/<task_id>)

@app.route("/api/v1/tasks/<task_id>", methods=["DELETE"])
def delete_tasks(task_id):
    """
    Выполняет "мягкое" удаление задачи: не удаляет из списка,
    а меняет статус на "cancelled" и устанавливает deleted_at.
    """
    task = find_task(task_id)#поиск задачи по id

    if task is None: # Если задача не найдена — ошибка 404
        return jsonify({"error": "Задача не найдена"}), 404

    #обновление полей для soft delete
    task["status"] = "cancelled" # Меняем статус на отменено
    task["deleted_at"] = datetime.datetime.now().isoformat()  # Фиксируем время удаления
    task["updated_at"] = datetime.datetime.now().isoformat()  # Обновляем время последнего изменения

    return jsonify(task), 200 # Возвращаем обновлённую задачу

# частично обновить задачу (PATCH /api/v1/tasks/<task_id>)
@app.route("/api/v1/tasks/<task_id>", methods=["PATCH"])
def patch_tasks(task_id):
    """
    Частично обновляет только указанные поля задачи.
    Остальные поля сохраняются без изменений.
    """
    data = request.get_json(silent=True) #получаем json из тела запроса

    # Если JSON не передан ошибка
    if not data:
        return jsonify({"error": "Отсутствуют данные JSON"}), 400

    # Ищем задачу по ID
    task = find_task(task_id)
    if task is None:
        return jsonify({"error": "Задача не найдена"}), 404

    # обновление поля status с валидацией
    if "status" in data:  # Если клиент передал поле status
        if data["status"] not in status_lst:  #проверка допустимость значения
            return jsonify({"error": "Поле `status` невалидно"}), 400
        task["status"] = data["status"]  #обновление значения

    #обновление поля priority с валидацией
    if "priority" in data:
        if data["priority"] not in priority_lst:
            return jsonify({"error": "Поле `priority` невалидно"}), 400
        task["priority"] = data["priority"]

    # обновление полей title и description
    if "title" in data:
        task["title"] = data["title"]
    if "description" in data:
        task["description"] = data["description"]

    # обновление времени последнего изменения
    task["updated_at"] = datetime.datetime.now().isoformat()

    return jsonify(task), 200 # возвращает обновлённую задачу

#запуск приложения
if __name__ == "__main__":
    """
    Этот блок выполняется только если файл запущен напрямую (не импортирован).
    Запускает Flask-сервер для разработки.
    """
    # Запускаем приложение:
    # host="0.0.0.0" — доступно не только с localhost, но и с других устройств в сети
    # port=5000 — стандартный порт для Flask
    # debug=True — включает режим отладки (авто-перезагрузка при изменении кода, подробные ошибки)
    app.run(host="0.0.0.0", port=5000, debug=True)