from PyQt6.QtCore import QThread, pyqtSignal
from config import wolfram


class CalculationThread(QThread):

    calculation_finished = pyqtSignal(list)
    calculation_error = pyqtSignal(str)
    calculation_started = pyqtSignal()

    def __init__(self, *params, model="lotka"):
        super().__init__()

        self.params = params
        self.model = model

    def run(self):
        try:

            self.calculation_started.emit()

            # ---------- ЛОТКА ВОЛЬТЕРРА ----------
            if self.model == "lotka":

                alpha, beta, gamma, delta, x0, y0 = self.params

                expr = f"""
                sol = NDSolve[{{
                    x'[t] == {alpha}*x[t] - {beta}*x[t]*y[t],
                    y'[t] == {delta}*x[t]*y[t] - {gamma}*y[t],
                    x[0] == {x0},
                    y[0] == {y0}
                }}, {{x, y}}, {{t, 0, 50}}];

                Table[{{
                    t,
                    Evaluate[x[t] /. sol[[1]]],
                    Evaluate[y[t] /. sol[[1]]]
                }}, {{t, 0, 50, 0.1}}]
                """

            # ---------- КОНКУРЕНЦИЯ ВИДОВ ----------
            elif self.model == "competition":

                p, q, r, s, t, u, x0, y0 = self.params

                expr = f"""
                sol = NDSolve[{{
                    x'[t] == x[t]*({p} - {q}*x[t] - {r}*y[t]),
                    y'[t] == y[t]*({s} - {t}*x[t] - {u}*y[t]),
                    x[0] == {x0},
                    y[0] == {y0}
                }}, {{x, y}}, {{t, 0, 7}}];

                Table[{{
                    t,
                    Evaluate[x[t] /. sol[[1]]],
                    Evaluate[y[t] /. sol[[1]]]
                }}, {{t, 0, 7, 0.1}}]
                """

            else:
                raise ValueError(f"Unknown model: {self.model}")

            result = wolfram.evaluate(expr)

            self.calculation_finished.emit(result)

        except Exception as e:
            self.calculation_error.emit(str(e))