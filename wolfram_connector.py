from wolframclient.evaluation import WolframLanguageSession
from wolframclient.language import wlexpr
import atexit

class WolframConnector:
    def __init__(self, kernel_path=None):
        if kernel_path:
            self.session = WolframLanguageSession(kernel_path)
        else:
            self.session = WolframLanguageSession()  # если путь прописан в PATH

        print("✅ Wolfram session started")
        atexit.register(self.close_session)

    def evaluate(self, expr: str):
        """Безопасное выполнение выражения"""
        try:
            return self.session.evaluate(wlexpr(expr))
        except Exception as e:
            print(f"❌ Wolfram error: {e}")
            return None

    def close_session(self):
        """Безопасно завершает сессию при выходе"""
        try:
            if self.session is not None:
                self.session.terminate()
                print("🧹 Wolfram session terminated.")
        except Exception as e:
            print(f"⚠️ Error closing Wolfram session: {e}")
