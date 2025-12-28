# calculation_thread.py
from PyQt6.QtCore import QThread, pyqtSignal
from config import wolfram

class CalculationThread(QThread):
    """Поток для вычислений в Wolfram"""
    calculation_finished = pyqtSignal(list)  # Сигнал с результатом
    calculation_error = pyqtSignal(str)  # Сигнал с ошибкой
    calculation_started = pyqtSignal()  # Сигнал начала вычислений

    def __init__(self, alpha, beta, gamma, delta, x0, y0):
        super().__init__()
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.delta = delta
        self.x0 = x0
        self.y0 = y0

    def run(self):
        try:
            self.calculation_started.emit()

            expr = f"""
            sol = NDSolve[{{
                x'[t] == {self.alpha}*x[t] - {self.beta}*x[t]*y[t],
                y'[t] == {self.delta}*x[t]*y[t] - {self.gamma}*y[t],
                x[0] == {self.x0},
                y[0] == {self.y0}
            }}, {{x, y}}, {{t, 0, 50}}];

            Table[{{
                t,
                Evaluate[x[t] /. sol[[1]]],
                Evaluate[y[t] /. sol[[1]]]
            }}, {{t, 0, 50, 0.1}}]
            """

            result = wolfram.evaluate(expr)
            self.calculation_finished.emit(result)

        except Exception as e:
            self.calculation_error.emit(str(e))