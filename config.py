from wolfram_connector import WolframConnector
from tinydb import TinyDB

WOLFRAM_PATH = r"C:\Program Files\Wolfram Research\Wolfram\14.3\WolframKernel.exe"

wolfram = WolframConnector(kernel_path=WOLFRAM_PATH)
db = TinyDB('calculations_db.json')