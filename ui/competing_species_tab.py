from datetime import datetime
import uuid

from core.calculation_thread import CalculationThread
from core.database import save_calculation, load_calculation

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QSpacerItem,
    QSizePolicy, QTabWidget, QProgressBar, QMessageBox
)

from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import numpy as np


class CompetingSpeciesTab(QWidget):
    """Вкладка: Модель конкуренции видов"""

    def __init__(self):
        super().__init__()

        self.animation = None
        self.current_frame = 0
        self.is_animating = False

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

        subtitle = QLabel("Введите параметры модели и запустите расчёт")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #AAAAAA; font-size: 13px;")

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

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

        form_layout.addRow("x₀:", self.x0_input)
        form_layout.addRow("y₀:", self.y0_input)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)

        self.calc_button = QPushButton("🔢 Рассчитать")
        self.calc_button.clicked.connect(self.on_calculate)

        self.clear_button = QPushButton("🧹 Очистить")
        self.clear_button.clicked.connect(self.on_clear)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(self.calc_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch(1)

        self.graph_tabs = QTabWidget()

        self.time_tab = QWidget()
        self.phase_tab = QWidget()
        self.vector_tab = QWidget()
        self.isocline_tab = QWidget()
        self.total_tab = QWidget()
        self.phase3d_tab = QWidget()
        self.animation_tab = QWidget()
        self.outcome_tab = QWidget()

        for tab in [
            self.time_tab,
            self.phase_tab,
            self.vector_tab,
            self.isocline_tab,
            self.total_tab,
            self.phase3d_tab,
            self.outcome_tab,
            self.animation_tab
        ]:
            tab.setLayout(QVBoxLayout())

        self.graph_tabs.addTab(self.time_tab, "Популяции по времени")
        self.graph_tabs.addTab(self.phase_tab, "Фазовый портрет")
        self.graph_tabs.addTab(self.vector_tab, "Векторное поле")
        self.graph_tabs.addTab(self.isocline_tab, "Изоклины")
        self.graph_tabs.addTab(self.total_tab, "Суммарная популяция")
        self.graph_tabs.addTab(self.phase3d_tab, "3D фазовый график")
        self.graph_tabs.addTab(self.outcome_tab, "Исход конкуренции")
        self.graph_tabs.addTab(self.animation_tab, "Анимация фазового портрета")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        layout.addLayout(form_layout)
        layout.addSpacing(10)
        layout.addWidget(self.progress_bar)
        layout.addSpacing(10)
        layout.addLayout(button_layout)
        layout.addSpacing(15)
        layout.addWidget(self.graph_tabs)

        layout.addItem(QSpacerItem(
            0, 10,
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Expanding
        ))

        self.setLayout(layout)

    def on_calculate(self):

        if self.calculation_thread and self.calculation_thread.isRunning():
            return

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

            self.calculation_thread.calculation_finished.connect(
                self.on_calculation_finished
            )

            self.calculation_thread.calculation_error.connect(
                self.on_calculation_error
            )

            self.calculation_thread.start()

        except Exception as e:
            self.show_error(str(e))

    def on_calculation_finished(self, result):

        self.calc_button.setEnabled(True)
        self.calc_button.setText("🔢 Рассчитать")
        self.progress_bar.setVisible(False)

        self.t_data = [float(row[0]) for row in result]
        self.x_data = [float(row[1]) for row in result]
        self.y_data = [float(row[2]) for row in result]

        self.plot_graphs(self.t_data, self.x_data, self.y_data)
        self.current_calc_id = None

    def on_calculation_error(self, error):

        self.calc_button.setEnabled(True)
        self.calc_button.setText("🔢 Рассчитать")
        self.progress_bar.setVisible(False)

        QMessageBox.critical(self, "Ошибка", error)

    def simulate_competition(self, x0, y0, p, q, r, s, t, u, steps=200, dt=0.05):

        x = x0
        y = y0

        for _ in range(steps):

            dx = x * (p - q * x - r * y)
            dy = y * (s - t * x - u * y)

            x += dx * dt
            y += dy * dt

            if x < 0:
                x = 0
            if y < 0:
                y = 0

        return x, y

    def plot_graphs(self, t, x, y):

        t = np.array(t, dtype=float)
        x = np.array(x, dtype=float)
        y = np.array(y, dtype=float)

        p = float(self.p_input.text())
        q = float(self.q_input.text())
        r = float(self.r_input.text())

        s = float(self.s_input.text())
        t_param = float(self.t_input.text())
        u = float(self.u_input.text())

        # -------- точка равновесия --------

        den = q * u - r * t_param

        equilibrium_x = None
        equilibrium_y = None

        if abs(den) > 1e-8:
            equilibrium_x = (p * u - r * s) / den
            equilibrium_y = (s * q - p * t_param) / den


        for tab in [
            self.time_tab,
            self.phase_tab,
            self.vector_tab,
            self.isocline_tab,
            self.total_tab,
            self.phase3d_tab,
            self.outcome_tab
        ]:
            layout = tab.layout()
            for i in reversed(range(layout.count())):
                w = layout.itemAt(i).widget()
                if w:
                    w.deleteLater()

        fig_time = Figure(figsize=(7, 4))
        fig_time.subplots_adjust(bottom=0.20)
        canvas_time = FigureCanvas(fig_time)
        ax = fig_time.add_subplot(111)

        ax.plot(t, x, label="Вид X")
        ax.plot(t, y, label="Вид Y")

        ax.set_xlabel("t")
        ax.set_ylabel("Популяция")
        ax.set_title("Динамика популяций")
        ax.legend()
        ax.grid(True)

        self.time_tab.layout().addWidget(canvas_time)

        fig_phase = Figure(figsize=(7, 4))
        fig_phase.subplots_adjust(bottom=0.20)
        canvas_phase = FigureCanvas(fig_phase)
        ax2 = fig_phase.add_subplot(111)

        ax2.plot(x, y)

        if equilibrium_x is not None and equilibrium_y is not None:
            ax2.scatter(equilibrium_x, equilibrium_y,
                        color="red", s=80, label="Равновесие")
            ax2.legend()

        ax2.set_xlabel("X")
        ax2.set_ylabel("Y")
        ax2.set_title("Фазовый портрет")
        ax2.grid(True)

        self.phase_tab.layout().addWidget(canvas_phase)



        X, Y = np.meshgrid(
            np.linspace(min(x)*0.8, max(x)*1.2, 20),
            np.linspace(min(y)*0.8, max(y)*1.2, 20)
        )

        U = X * (p - q*X - r*Y)
        V = Y * (s - t_param*X - u*Y)

        fig_vector = Figure(figsize=(7, 4))
        fig_vector.subplots_adjust(bottom=0.20)
        canvas_vector = FigureCanvas(fig_vector)

        ax3 = fig_vector.add_subplot(111)

        ax3.quiver(X, Y, U, V)
        ax3.plot(x, y)

        ax3.set_xlabel("X")
        ax3.set_ylabel("Y")
        ax3.set_title("Векторное поле")

        self.vector_tab.layout().addWidget(canvas_vector)

        # -------- Суммарная популяция --------

        fig_total = Figure(figsize=(7, 4))
        fig_total.subplots_adjust(bottom=0.20)
        canvas_total = FigureCanvas(fig_total)

        ax_total = fig_total.add_subplot(111)

        total = x + y

        ax_total.plot(t, total)

        ax_total.set_xlabel("t")
        ax_total.set_ylabel("X + Y")
        ax_total.set_title("Суммарная популяция")

        ax_total.grid(True)

        self.total_tab.layout().addWidget(canvas_total)

        # -------- Изоклины --------

        fig_iso = Figure(figsize=(8, 5))
        fig_iso.subplots_adjust(bottom=0.20)
        canvas_iso = FigureCanvas(fig_iso)
        ax = fig_iso.add_subplot(111)

        # Параметры (с защитой от пустых строк)
        try:
            p = float(self.p_input.text() or 1)
            q = float(self.q_input.text() or 1)
            r = float(self.r_input.text() or 1)
            s = float(self.s_input.text() or 1)
            t_param = float(self.t_input.text() or 1)
            u = float(self.u_input.text() or 1)
        except ValueError:
            p, q, r, s, t_param, u = 1.0, 1.0, 1.0, 1.0, 1.0, 1.0

        # 1. СЕТКА (Ключевое исправление: используем 1D массивы для осей)
        x_range = np.linspace(0.01, 3.5, 50).astype(float)
        y_range = np.linspace(0.01, 2.5, 50).astype(float)

        # Создаем 2D сетку только для расчета DX и DY
        X_mesh, Y_mesh = np.meshgrid(x_range, y_range)

        # Уравнения системы
        DX = (X_mesh * (p - q * X_mesh - r * Y_mesh)).astype(float)
        DY = (Y_mesh * (s - t_param * X_mesh - u * Y_mesh)).astype(float)

        # Фильтрация нечисловых значений
        DX = np.nan_to_num(DX)
        DY = np.nan_to_num(DY)

        # Рисуем поток (streamlines)
        # ПЕРЕДАЕМ x_range и y_range как 1D массивы! Это решает проблему с sanitize_sequence
        try:
            # broken_streamlines=False — это ключ к тому, чтобы линии не обрывались
            # integration_direction='both' — рисует линию в обе стороны от точки старта
            strm = ax.streamplot(x_range, y_range, DX, DY,
                                 color='black',
                                 linewidth=0.5,
                                 density=0.75,
                                 arrowstyle='-',  # Убираем стрелки
                                 integration_direction='both',
                                 broken_streamlines=False)  # ЗАПРЕЩАЕМ ОБРЫВЫ

            if hasattr(strm, 'lines'):
                strm.lines.set_alpha(0.8)  # Делаем чуть прозрачнее, так как линий станет много

        except Exception as e:
            # Если ваша версия Matplotlib очень старая и не знает про broken_streamlines
            strm = ax.streamplot(x_range, y_range, DX, DY,
                                 color='black', linewidth=0.5,
                                 density=2.5, arrowstyle='-')

        # 2. Построение НУЛЬ-ИЗОКЛИН
        x_vals = np.linspace(0, 3.5, 200)
        # Используем np.maximum, чтобы графики не уходили в отрицательную область
        y_iso1 = np.maximum(0, (p - q * x_vals) / r)
        y_iso2 = np.maximum(0, (s - t_param * x_vals) / u)

        ax.plot(x_vals, y_iso1, color="blue", linewidth=2, label="dx/dt = 0 (X-nullcline)")
        ax.plot(x_vals, y_iso2, color="red", linewidth=2, label="dy/dt = 0 (Y-nullcline)")

        # 3. ТОЧКА РАВНОВЕСИЯ
        denom = (q * u - r * t_param)
        if abs(denom) > 1e-6:
            x_eq = (p * u - r * s) / denom
            y_eq = (s * q - p * t_param) / denom
            if x_eq >= 0 and y_eq >= 0:
                ax.scatter([x_eq], [y_eq], color='green', s=60, zorder=5, edgecolors='black')
                ax.text(x_eq + 0.05, y_eq + 0.05, f" Равновесие ({x_eq:.2f}, {y_eq:.2f})")

        # Основная траектория (которая считается решателем)
        ax.plot(x, y, linewidth=2.5, color="darkgreen", label="Текущее решение")

        # 4. ОФОРМЛЕНИЕ
        ax.set_xlim(0, 3.2)
        ax.set_ylim(0, 2.2)
        ax.set_xlabel("Популяция X")
        ax.set_ylabel("Популяция Y")
        ax.set_title("Фазовый портрет: Конкуренция видов")
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.legend(loc='upper right')

        # Очистка старого виджета перед добавлением (если нужно)
        self.isocline_tab.layout().addWidget(canvas_iso)

        # -------- 3D фазовый график --------

        fig3d = Figure(figsize=(7, 4))
        fig3d.subplots_adjust(bottom=0.20)
        canvas3d = FigureCanvas(fig3d)

        ax3d = fig3d.add_subplot(111, projection='3d')

        ax3d.plot(x, y, t)

        ax3d.set_xlabel("X")
        ax3d.set_ylabel("Y")
        ax3d.set_zlabel("t")

        ax3d.set_title("3D фазовый график")

        self.phase3d_tab.layout().addWidget(canvas3d)

        # -------- карта исходов конкуренции --------

        fig_out = Figure(figsize=(7, 4))
        fig_out.subplots_adjust(bottom=0.20)
        canvas_out = FigureCanvas(fig_out)

        ax_out = fig_out.add_subplot(111)

        p = float(self.p_input.text())
        q = float(self.q_input.text())
        r = float(self.r_input.text())

        s = float(self.s_input.text())
        t_param = float(self.t_input.text())
        u = float(self.u_input.text())

        x_vals = np.linspace(0, max(x) * 1.5, 40)
        y_vals = np.linspace(0, max(y) * 1.5, 40)

        result = np.zeros((len(y_vals), len(x_vals)))

        for i, x0 in enumerate(x_vals):
            for j, y0 in enumerate(y_vals):

                xf, yf = self.simulate_competition(
                    x0, y0,
                    p, q, r,
                    s, t_param, u
                )

                if xf > yf:
                    result[j, i] = 1
                else:
                    result[j, i] = 2

        im = ax_out.imshow(
            result,
            extent=[x_vals.min(), x_vals.max(), y_vals.min(), y_vals.max()],
            origin="lower",
            aspect="auto"
        )

        ax_out.set_xlabel("Начальная популяция X₀")
        ax_out.set_ylabel("Начальная популяция Y₀")
        ax_out.set_title("Исход конкуренции видов")


        self.outcome_tab.layout().addWidget(canvas_out)

    def on_clear(self):

        self.p_input.setText("2")
        self.q_input.setText("0.66")
        self.r_input.setText("2")

        self.s_input.setText("2")
        self.t_input.setText("1.33")
        self.u_input.setText("1")

        self.x0_input.setText("3.5")
        self.y0_input.setText("2")

        self.t_data = []
        self.x_data = []
        self.y_data = []

        self.current_calc_id = None

    def save_current_calculation(self):
        """Сохраняет текущий расчет в базу данных"""

        if not self.t_data:
            QMessageBox.warning(self, "Предупреждение",
                                "Нет данных для сохранения! Сначала выполните расчет.")
            return False

        if not self.current_calc_id:
            self.current_calc_id = str(uuid.uuid4())

        calc_data = {
            'id': self.current_calc_id,
            'model_name': 'Конкуренция видов',

            'p': float(self.p_input.text()),
            'q': float(self.q_input.text()),
            'r': float(self.r_input.text()),
            's': float(self.s_input.text()),
            't': float(self.t_input.text()),
            'u': float(self.u_input.text()),

            'x0': float(self.x0_input.text()),
            'y0': float(self.y0_input.text()),

            'timestamp': datetime.now().isoformat(),

            't_data': [float(t) for t in self.t_data],
            'x_data': [float(x) for x in self.x_data],
            'y_data': [float(y) for y in self.y_data]
        }

        result = save_calculation(calc_data)

        QMessageBox.information(self, "Сохранение", result)

        return True

    def load_calculation_by_id(self, calc_id):
        """Загружает расчет из базы"""

        result = load_calculation(calc_id)

        if result:

            calc = result
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
                self.t_data = calc['t_data']
                self.x_data = calc['x_data']
                self.y_data = calc['y_data']

                self.plot_graphs(self.t_data, self.x_data, self.y_data)

            return True

        return False