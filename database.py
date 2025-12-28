# database.py
from tinydb import TinyDB, Query
from datetime import datetime
import uuid
from config import db

Calculation = Query()


def save_calculation(calc_data):
    """Сохраняет или обновляет расчет в базе данных"""
    if 'id' in calc_data:
        # Проверяем, существует ли уже такой расчет
        existing = db.search(Calculation.id == calc_data['id'])

        if existing:
            # Обновляем существующую запись
            db.update(calc_data, Calculation.id == calc_data['id'])
            return "Расчет обновлен!"
        else:
            # Добавляем новую запись
            db.insert(calc_data)
            return "Расчет сохранен!"
    else:
        # Создаем новый ID и сохраняем
        calc_data['id'] = str(uuid.uuid4())
        db.insert(calc_data)
        return "Расчет сохранен!"


def load_calculation_by_id(calc_id):
    """Загружает расчет по ID"""
    result = db.search(Calculation.id == calc_id)
    return result[0] if result else None


def get_all_calculations():
    """Возвращает все сохраненные расчеты"""
    return db.all()


def clear_all_history():
    """Очищает всю историю расчетов"""
    db.truncate()
    return "Вся история расчетов удалена!"


def prepare_calculation_data(alpha, beta, gamma, delta, x0, y0, t_data, x_data, y_data, calc_id=None):
    """Подготавливает данные для сохранения"""
    calc_data = {
        'model_name': 'Лотка-Вольтерра',
        'alpha': float(alpha) if alpha else 0.0,
        'beta': float(beta) if beta else 0.0,
        'gamma': float(gamma) if gamma else 0.0,
        'delta': float(delta) if delta else 0.0,
        'x0': float(x0) if x0 else 0.0,
        'y0': float(y0) if y0 else 0.0,
        'timestamp': datetime.now().isoformat(),
        't_data': [float(t) for t in t_data],
        'x_data': [float(x) for x in x_data],
        'y_data': [float(y) for y in y_data]
    }

    if calc_id:
        calc_data['id'] = calc_id

    return calc_data