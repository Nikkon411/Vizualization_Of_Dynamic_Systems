

from tinydb import TinyDB, Query
from config import db

def save_calculation(calc_data):
    calculation = Query()
    existing = db.search(calculation.id == calc_data['id'])

    if existing:
        db.update(calc_data, calculation.id == calc_data['id'])
        return "Расчет обновлен!"
    else:
        db.insert(calc_data)
        return "Расчет сохранен!"


def load_calculation(calc_id):
    calculation = Query()
    result = db.search(calculation.id == calc_id)
    return result[0] if result else None


def get_all_calculations():
    calculations = db.all()
    calculations.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return calculations


def clear_all():
    db.truncate()