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

                # ---------- МОДЕЛЬ SEIR ----------

            elif self.model == "seir":

                # Принимаем параметры для SEIR

                beta, alpha, gamma, S0, E0, I0, R0, t_max = self.params

                # Добавлено уравнение для E'[t] и параметр alpha

                expr = f"""
                        sol = NDSolve[{{
                            S'[t] == -{beta}*S[t]*Inf[t],
                            Ex'[t] == {beta}*S[t]*Inf[t] - {alpha}*Ex[t],
                            Inf'[t] == {alpha}*Ex[t] - {gamma}*Inf[t],
                            R'[t] == {gamma}*Inf[t],
                            S[0] == {S0},
                            Ex[0] == {E0},
                            Inf[0] == {I0},
                            R[0] == {R0}
                        }}, {{S, Ex, Inf, R}}, {{t, 0, {t_max}}}];

                        Table[{{
                            t,
                            Evaluate[S[t] /. sol[[1]]],
                            Evaluate[Ex[t] /. sol[[1]]],
                            Evaluate[Inf[t] /. sol[[1]]],
                            Evaluate[R[t] /. sol[[1]]]
                        }}, {{t, 0, {t_max}, 0.5}}]
                        """
            elif self.model == "islm":
                # Распаковываем 12 параметров
                G, C0, MPC, I0, d, Ms, P, k, h, Y0, i0, t_max = self.params

                # Коэффициенты скорости (можно оставить 0.1 или сделать s_i чуть быстрее)
                s_y = 0.1
                s_i = 0.05

                expr = f"""
                sol = NDSolve[{{
                    Y'[t] == {s_y} * ({C0} + {MPC}*Y[t] + {I0} - {d}*rate[t] + {G} - Y[t]),
                    rate'[t] == {s_i} * ({k}*Y[t] - {h}*rate[t] - {Ms}/{P}),

                    Y[0] == {Y0},
                    rate[0] == {i0}
                }}, {{Y, rate}}, {{t, 0, {t_max}}}];

                Table[{{
                    t,
                    Evaluate[Y[t] /. sol[[1]]],
                    Evaluate[rate[t] /. sol[[1]]]
                }}, {{t, 0, {t_max}, 0.5}}]
                """


            else:
                raise ValueError(f"Unknown model: {self.model}")

            result = wolfram.evaluate(expr)

            self.calculation_finished.emit(result)

        except Exception as e:
            self.calculation_error.emit(str(e))