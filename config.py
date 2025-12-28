# config.py
from wolfram_connector import WolframConnector
from tinydb import TinyDB

# путь к ядру
WOLFRAM_PATH = r"C:\Program Files\Wolfram Research\Wolfram\14.3\WolframKernel.exe"

# Инициализация Wolfram
wolfram = WolframConnector(kernel_path=WOLFRAM_PATH)

# Инициализация базы данных
db = TinyDB('calculations_db.json')