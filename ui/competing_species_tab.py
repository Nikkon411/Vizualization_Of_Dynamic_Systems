from datetime import datetime
import uuid
import numpy as np

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QSpacerItem,
    QSizePolicy, QTabWidget, QProgressBar, QMessageBox
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from core.calculation_thread import CalculationThread
from core.database import save_calculation, load_calculation


class CompetingSpeciesTab(QWidget):
    """Вкладка: Модель конкуренции видов"""

    def __init__(self):
        super().__init__()

        self.t_data = []
        self.x_data = []
        self.y_data = []

        self.calculation_thread = None
        self.current_calc_id = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("Система конкуренции видов")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form_layout = QFormLayout()

        # Параметры модели (как в SEIR)
        self.p_input = QLineEdit("2")
        self.q_input = QLineEdit("0.66")
        self.r_input = QLineEdit("2")
        self.s_input = QLineEdit("2")
        self.t_input = QLineEdit("1.33")
        self.u_input = QLineEdit("1")
        self.x0_input = QLineEdit("3.5")
        self.y0_input = QLineEdit("2")

        form_layout.addRow("p (рост вида X):", self.p_input)
        form_layout.addRow("q (конкуренция X):", self.q_input)
        form_layout.addRow("r (влияние Y на X):", self.r_input)
        form_layout.addRow("s (рост вида Y):", self.s_input)
        form_layout.addRow("t (влияние X на Y):", self.t_input)
        form_layout.addRow("u (конкуренция Y):", self.u_input)
        form_layout.addRow("x₀ (нач. популяция X):", self.x0_input)
        form_layout.addRow("y₀ (нач. популяция Y):", self.y0_input)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)

        self.calc_button = QPushButton("Рассчитать")
        self.calc_button.clicked.connect(self.on_calculate)

        self.graph_tabs = QTabWidget()

        # Создание вкладок
        self.time_tab = QWidget()
        self.phase_tab = QWidget()
        self.vector_tab = QWidget()
        self.isocline_tab = QWidget()
        self.total_tab = QWidget()
        self.phase3d_tab = QWidget()
        self.outcome_tab = QWidget()

        for tab in [self.time_tab, self.phase_tab, self.vector_tab,
                    self.isocline_tab, self.total_tab, self.phase3d_tab, self.outcome_tab]:
            tab.setLayout(QVBoxLayout())

        self.graph_tabs.addTab(self.time_tab, "Динамика во времени")
        self.graph_tabs.addTab(self.phase_tab, "Фазовый портрет")
        self.graph_tabs.addTab(self.vector_tab, "Векторное поле")
        self.graph_tabs.addTab(self.isocline_tab, "Изоклины")
        self.graph_tabs.addTab(self.total_tab, "Суммарная популяция")
        self.graph_tabs.addTab(self.phase3d_tab, "3D фазовый график")
        self.graph_tabs.addTab(self.outcome_tab, "Исход конкуренции")

        layout.addWidget(title)
        layout.addLayout(form_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.calc_button)
        layout.addWidget(self.graph_tabs)

        self.setLayout(layout)

    def on_calculate(self):
        try:
            p = self.p_input.text()
            q = self.q_input.text()
            r = self.r_input.text()
            s = self.s_input.text()
            t = self.t_input.text()
            u = self.u_input.text()
            x0 = self.x0_input.text()
            y0 = self.y0_input.text()

            if not all([p, q, r, s, t, u, x0, y0]):
                QMessageBox.warning(self, "Предупреждение", "Заполните все поля!")
                return

            self.calc_button.setEnabled(False)
            self.calc_button.setText("⏳ Вычисление...")
            self.progress_bar.setVisible(True)

            self.calculation_thread = CalculationThread(
                p, q, r, s, t, u, x0, y0,
                model="competition"
            )
            self.calculation_thread.calculation_finished.connect(self.on_finished)
            self.calculation_thread.calculation_error.connect(self.on_error)
            self.calculation_thread.start()

        except Exception as e:
            self.on_error(str(e))

    def on_error(self, error):
        self.calc_button.setEnabled(True)
        self.calc_button.setText("Рассчитать")
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Ошибка", f"Ошибка расчета:\n{error}")

    def on_finished(self, result):
        self.calc_button.setEnabled(True)
        self.calc_button.setText("Рассчитать")
        self.progress_bar.setVisible(False)

        self.t_data = [float(row[0]) for row in result]
        self.x_data = [float(row[1]) for row in result]
        self.y_data = [float(row[2]) for row in result]

        self.current_calc_id = None
        self.plot_graphs(self.t_data, self.x_data, self.y_data)

    def simulate_competition(self, x0, y0, p, q, r, s, t, u, steps=200, dt=0.05):
        x, y = x0, y0
        for _ in range(steps):
            dx = x * (p - q * x - r * y)
            dy = y * (s - t * x - u * y)
            x += dx * dt
            y += dy * dt
            if x < 0: x = 0
            if y < 0: y = 0
        return x, y

    def plot_graphs(self, t, x, y):
        # ВАША ОРИГИНАЛЬНАЯ ЛОГИКА РАСЧЕТОВ (без изменений)
        t = np.array(t, dtype=float)
        x = np.array(x, dtype=float)
        y = np.array(y, dtype=float)

        p = float(self.p_input.text())
        q = float(self.q_input.text())
        r = float(self.r_input.text())
        s = float(self.s_input.text())
        t_param = float(self.t_input.text())
        u = float(self.u_input.text())

        den = q * u - r * t_param
        equilibrium_x = None
        equilibrium_y = None

        if abs(den) > 1e-8:
            equilibrium_x = (p * u - r * s) / den
            equilibrium_y = (s * q - p * t_param) / den

        for tab in [self.time_tab, self.phase_tab, self.vector_tab,
                    self.isocline_tab, self.total_tab, self.phase3d_tab, self.outcome_tab]:
            layout = tab.layout()
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        # 1. По времени
        fig_time = Figure(figsize=(7, 4))
        fig_time.subplots_adjust(bottom=0.20)
        canvas_time = FigureCanvas(fig_time)
        ax1 = fig_time.add_subplot(111)
        ax1.plot(t, x, label="Вид X"); ax1.plot(t, y, label="Вид Y")
        ax1.set_xlabel("t"); ax1.set_ylabel("Популяция"); ax1.set_title("Динамика популяций")
        ax1.legend(); ax1.grid(True)
        self.time_tab.layout().addWidget(NavigationToolbar(canvas_time, self))
        self.time_tab.layout().addWidget(canvas_time)

        # 2. Фазовый портрет
        fig_phase = Figure(figsize=(7, 4))
        fig_phase.subplots_adjust(bottom=0.20)
        canvas_phase = FigureCanvas(fig_phase)
        ax2 = fig_phase.add_subplot(111)
        ax2.plot(x, y)
        if equilibrium_x is not None and equilibrium_y is not None:
            ax2.scatter(equilibrium_x, equilibrium_y, color="red", s=80, label="Равновесие")
            ax2.legend()
        ax2.set_xlabel("X"); ax2.set_ylabel("Y"); ax2.set_title("Фазовый портрет"); ax2.grid(True)
        self.phase_tab.layout().addWidget(NavigationToolbar(canvas_phase, self))
        self.phase_tab.layout().addWidget(canvas_phase)

        # 3. Векторное поле
        fig_vector = Figure(figsize=(7, 4))
        fig_vector.subplots_adjust(bottom=0.20)
        canvas_vector = FigureCanvas(fig_vector)
        ax3 = fig_vector.add_subplot(111)
        X_m, Y_m = np.meshgrid(np.linspace(min(x)*0.8, max(x)*1.2, 20), np.linspace(min(y)*0.8, max(y)*1.2, 20))
        U = X_m * (p - q*X_m - r*Y_m); V = Y_m * (s - t_param*X_m - u*Y_m)
        ax3.quiver(X_m, Y_m, U, V); ax3.plot(x, y)
        ax3.set_xlabel("X"); ax3.set_ylabel("Y"); ax3.set_title("Векторное поле")
        self.vector_tab.layout().addWidget(NavigationToolbar(canvas_vector, self))
        self.vector_tab.layout().addWidget(canvas_vector)

        # 4. Суммарная популяция
        fig_total = Figure(figsize=(7, 4))
        fig_total.subplots_adjust(bottom=0.20)
        canvas_total = FigureCanvas(fig_total)
        ax_total = fig_total.add_subplot(111)
        ax_total.plot(t, x + y); ax_total.set_xlabel("t"); ax_total.set_ylabel("X + Y"); ax_total.set_title("Суммарная популяция"); ax_total.grid(True)
        self.total_tab.layout().addWidget(NavigationToolbar(canvas_total, self))
        self.total_tab.layout().addWidget(canvas_total)

        # 5. Изоклины (ваша сложная логика)
        fig_iso = Figure(figsize=(8, 5))
        fig_iso.subplots_adjust(bottom=0.20)
        canvas_iso = FigureCanvas(fig_iso)
        ax_iso = fig_iso.add_subplot(111)
        xr = np.linspace(0.01, 3.5, 50).astype(float); yr = np.linspace(0.01, 2.5, 50).astype(float)
        XM, YM = np.meshgrid(xr, yr)
        DX = (XM * (p - q * XM - r * YM)); DY = (YM * (s - t_param * XM - u * YM))
        try:
            ax_iso.streamplot(xr, yr, np.nan_to_num(DX), np.nan_to_num(DY), color='black', linewidth=0.5, density=0.75, arrowstyle='-', integration_direction='both', broken_streamlines=False)
        except:
            ax_iso.streamplot(xr, yr, np.nan_to_num(DX), np.nan_to_num(DY), color='black', linewidth=0.5, density=2.5, arrowstyle='-')
        xv = np.linspace(0, 3.5, 200)
        ax_iso.plot(xv, np.maximum(0, (p - q * xv) / r), color="blue", label="dx/dt = 0")
        ax_iso.plot(xv, np.maximum(0, (s - t_param * xv) / u), color="red", label="dy/dt = 0")
        if equilibrium_x is not None and equilibrium_x >= 0:
            ax_iso.scatter([equilibrium_x], [equilibrium_y], color='green', s=60, zorder=5)
        ax_iso.plot(x, y, linewidth=2.5, color="darkgreen", label="Решение")
        ax_iso.set_xlim(0, 3.2); ax_iso.set_ylim(0, 2.2); ax_iso.legend()
        self.isocline_tab.layout().addWidget(NavigationToolbar(canvas_iso, self))
        self.isocline_tab.layout().addWidget(canvas_iso)

        # 6. 3D
        fig3d = Figure(figsize=(7, 4))
        fig3d.subplots_adjust(bottom=0.20)
        canvas3d = FigureCanvas(fig3d)
        ax3d = fig3d.add_subplot(111, projection='3d')
        ax3d.plot(x, y, t); ax3d.set_title("3D фазовый график")
        self.phase3d_tab.layout().addWidget(NavigationToolbar(canvas3d, self))
        self.phase3d_tab.layout().addWidget(canvas3d)

        # 7. Карта исходов
        fig_out = Figure(figsize=(7, 4))
        fig_out.subplots_adjust(bottom=0.20)
        canvas_out = FigureCanvas(fig_out)
        ax_out = fig_out.add_subplot(111)
        xv_m = np.linspace(0, max(x) * 1.5, 40); yv_m = np.linspace(0, max(y) * 1.5, 40)
        res = np.zeros((len(yv_m), len(xv_m)))
        for i, x0i in enumerate(xv_m):
            for j, y0j in enumerate(yv_m):
                xf, yf = self.simulate_competition(x0i, y0j, p, q, r, s, t_param, u)
                res[j, i] = 1 if xf > yf else 2
        ax_out.imshow(res, extent=[0, xv_m.max(), 0, yv_m.max()], origin="lower", aspect="auto")
        ax_out.set_xlabel("Начальная численность вида X")
        ax_out.set_ylabel("Начальная численность вида Y")
        ax_out.set_title("Карта выживания в зависимости от старта")
        self.outcome_tab.layout().addWidget(NavigationToolbar(canvas_out, self))
        self.outcome_tab.layout().addWidget(canvas_out)

    def save_current_calculation(self):
        if not self.t_data:
            QMessageBox.warning(self, "Предупреждение", "Нет данных для сохранения!")
            return False
        if not self.current_calc_id: self.current_calc_id = str(uuid.uuid4())
        calc_data = {
            'id': self.current_calc_id, 'model_name': 'Конкуренция видов',
            'p': float(self.p_input.text()), 'q': float(self.q_input.text()), 'r': float(self.r_input.text()),
            's': float(self.s_input.text()), 't': float(self.t_input.text()), 'u': float(self.u_input.text()),
            'x0': float(self.x0_input.text()), 'y0': float(self.y0_input.text()),
            'timestamp': datetime.now().isoformat(),
            't_data': self.t_data, 'x_data': self.x_data, 'y_data': self.y_data
        }
        QMessageBox.information(self, "Сохранение", save_calculation(calc_data))
        return True

    def load_calculation_by_id(self, calc_id):
        calc = load_calculation(calc_id)
        if calc:
            self.current_calc_id = calc_id
            self.p_input.setText(str(calc.get('p', '2')))
            self.q_input.setText(str(calc.get('q', '0.66')))
            self.r_input.setText(str(calc.get('r', '2')))
            self.s_input.setText(str(calc.get('s', '2')))
            self.t_input.setText(str(calc.get('t', '1.33')))
            self.u_input.setText(str(calc.get('u', '1')))
            self.x0_input.setText(str(calc.get('x0', '3.5')))
            self.y0_input.setText(str(calc.get('y0', '2')))
            if 't_data' in calc:
                self.t_data, self.x_data, self.y_data = calc['t_data'], calc['x_data'], calc['y_data']
                self.plot_graphs(self.t_data, self.x_data, self.y_data)
            return True
        return False