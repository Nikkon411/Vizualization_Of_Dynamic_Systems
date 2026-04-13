import uuid
import numpy as np
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel,
    QLineEdit, QPushButton, QProgressBar, QMessageBox, QTabWidget
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D

from core.calculation_thread import CalculationThread
from core.database import save_calculation, load_calculation

class HindmarshRoseTab(QWidget):
    """Вкладка: Модель нейронной активности Хиндмарша — Роуза"""

    def __init__(self):
        super().__init__()
        self.t_data, self.x_data, self.y_data, self.z_data = [], [], [], []
        self.calculation_thread = None
        self.current_calc_id = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Модель Хиндмарша — Роуза: Нейронная динамика")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form_layout = QFormLayout()

        # Параметры модели (стандартные значения для берстинга)
        self.a_input = QLineEdit("1.0")
        self.b_input = QLineEdit("3.0")
        self.c_input = QLineEdit("1.0")
        self.d_input = QLineEdit("5.0")
        self.r_input = QLineEdit("0.006")
        self.s_input = QLineEdit("4.0")
        self.i_input = QLineEdit("3.1")  # Внешний ток

        # Начальные условия
        self.x0_input = QLineEdit("-1.6")
        self.y0_input = QLineEdit("-1.0")
        self.z0_input = QLineEdit("1.0")
        self.t_max_input = QLineEdit("1000")

        form_layout.addRow("Параметр a:", self.a_input)
        form_layout.addRow("Параметр b:", self.b_input)
        form_layout.addRow("Параметр c:", self.c_input)
        form_layout.addRow("Параметр d:", self.d_input)
        form_layout.addRow("Скорость адаптации r:", self.r_input)
        form_layout.addRow("Параметр s:", self.s_input)
        form_layout.addRow("Внешний ток I:", self.i_input)
        form_layout.addRow("Нач. x (потенциал):", self.x0_input)
        form_layout.addRow("Нач. y (быстрая):", self.y0_input)
        form_layout.addRow("Нач. z (медленная):", self.z0_input)
        form_layout.addRow("Время T max:", self.t_max_input)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)

        self.calc_button = QPushButton("Рассчитать нейрон")
        self.calc_button.clicked.connect(self.on_calculate)

        self.graph_tabs = QTabWidget()
        # Растягиваем вкладки по всей ширине

        # Более надежный способ для Qt6 без вычислений вручную:
        self.graph_tabs.setTabBarAutoHide(False)
        self.graph_tabs.tabBar().setExpanding(True)  # Растягивание
        self.graph_tabs.tabBar().setDocumentMode(True)  # Убирает лишние рамки

        self.time_tab = QWidget()
        self.adaptation_tab = QWidget()  # Новая
        self.combined_tab = QWidget()  # Новая
        self.phase_2d_tab = QWidget()
        self.phase_3d_tab = QWidget()
        self.isi_hist_tab = QWidget()  # Вкладка для гистограммы
        self.isi_seq_tab = QWidget()

        self.tabs_list = [
            self.time_tab, self.adaptation_tab,
            self.combined_tab, self.phase_2d_tab, self.phase_3d_tab, self.isi_hist_tab, self.isi_seq_tab
        ]
        for tab in self.tabs_list:
            tab.setLayout(QVBoxLayout())

        self.graph_tabs.addTab(self.time_tab, "Потенциал x(t)")
        self.graph_tabs.addTab(self.adaptation_tab, "Адаптация z(t)")
        self.graph_tabs.addTab(self.combined_tab, "Совмещенный (x+z)")
        self.graph_tabs.addTab(self.phase_2d_tab, "Фазовое (x-y)")
        self.graph_tabs.addTab(self.phase_3d_tab, "3D Аттрактор")
        self.graph_tabs.addTab(self.isi_hist_tab, "Гистограмма ISI")
        self.graph_tabs.addTab(self.isi_seq_tab, "Динамика ISI")

        layout.addWidget(title)
        layout.addLayout(form_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.calc_button)
        layout.addWidget(self.graph_tabs)
        self.setLayout(layout)

    def on_calculate(self):
        try:
            params = [
                self.a_input.text(), self.b_input.text(), self.c_input.text(),
                self.d_input.text(), self.r_input.text(), self.s_input.text(),
                self.i_input.text(), self.x0_input.text(), self.y0_input.text(),
                self.z0_input.text(), self.t_max_input.text()
            ]

            if not all(params):
                QMessageBox.warning(self, "Предупреждение", "Заполните все параметры!")
                return

            self.calc_button.setEnabled(False)
            self.progress_bar.setVisible(True)

            self.calculation_thread = CalculationThread(*params, model="hindmarsh_rose")
            self.calculation_thread.calculation_finished.connect(self.on_finished)
            self.calculation_thread.calculation_error.connect(self.on_error)
            self.calculation_thread.start()
        except Exception as e:
            self.on_error(str(e))

    def on_finished(self, result):
        self.calc_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        if not result: return

        self.t_data = [float(r[0]) for r in result]
        self.x_data = [float(r[1]) for r in result]
        self.y_data = [float(r[2]) for r in result]
        self.z_data = [float(r[3]) for r in result]

        self.plot_graphs()

    def on_error(self, error):
        self.calc_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Ошибка", f"Ошибка: {error}")

    def plot_graphs(self):
        for tab in self.tabs_list:
            while tab.layout().count():
                child = tab.layout().takeAt(0)
                if child.widget(): child.widget().deleteLater()

        # 1. Временная динамика x(t)
        fig1 = Figure(figsize=(8, 4))
        fig1.subplots_adjust(bottom=0.20)
        canvas1 = FigureCanvas(fig1)
        ax1 = fig1.add_subplot(111)
        ax1.plot(self.t_data, self.x_data, color='crimson', lw=1)
        ax1.set_title("Мембранный потенциал (Bursting)")
        ax1.set_xlabel("t")
        ax1.set_ylabel("x")
        ax1.grid(True, alpha=0.3)
        self.time_tab.layout().addWidget(NavigationToolbar(canvas1, self))
        self.time_tab.layout().addWidget(canvas1)

        # --- 2. Медленная переменная z(t) ---
        fig_z = Figure(figsize=(8, 4))
        fig_z.subplots_adjust(bottom=0.20)
        canvas_z = FigureCanvas(fig_z)
        ax_z = fig_z.add_subplot(111)
        ax_z.plot(self.t_data, self.z_data, color='darkorange', lw=1.5)
        ax_z.set_title("Динамика переменной адаптации (медленный ток)")
        ax_z.set_xlabel("t")
        ax_z.set_ylabel("z")
        ax_z.grid(True, alpha=0.3)
        self.adaptation_tab.layout().addWidget(NavigationToolbar(canvas_z, self))
        self.adaptation_tab.layout().addWidget(canvas_z)

        # --- 3. Совмещенный график (x и z) ---
        fig_comb = Figure(figsize=(8, 4))
        fig_comb.subplots_adjust(bottom=0.20)
        canvas_comb = FigureCanvas(fig_comb)
        ax_comb_x = fig_comb.add_subplot(111)
        ax_comb_z = ax_comb_x.twinx()  # Вторая ось Y

        ax_comb_x.plot(self.t_data, self.x_data, color='crimson', lw=0.6, alpha=0.5, label="x (Потенциал)")
        ax_comb_z.plot(self.t_data, self.z_data, color='darkorange', lw=2, label="z (Адаптация)")

        ax_comb_x.set_ylabel("x", color='crimson')
        ax_comb_z.set_ylabel("z", color='darkorange')
        ax_comb_x.set_title("Влияние адаптации на Bursting")
        self.combined_tab.layout().addWidget(NavigationToolbar(canvas_comb, self))
        self.combined_tab.layout().addWidget(canvas_comb)

        # 2. 2D Фазовый портрет
        fig2 = Figure(figsize=(6, 6))
        fig2.subplots_adjust(bottom=0.20)
        canvas2 = FigureCanvas(fig2)
        ax2 = fig2.add_subplot(111)
        ax2.plot(self.x_data, self.y_data, color='navy', lw=0.7, alpha=0.8)
        ax2.scatter(self.x_data[0], self.y_data[0], color='green', s=40, label='Старт', zorder=5)
        ax2.scatter(self.x_data[-1], self.y_data[-1], color='red', s=60, label='Конец', zorder=5)
        ax2.set_title("Фазовая плоскость x-y")
        ax2.set_xlabel("x")
        ax2.set_ylabel("y")
        ax2.grid(True, alpha=0.3)
        self.phase_2d_tab.layout().addWidget(NavigationToolbar(canvas2, self))
        self.phase_2d_tab.layout().addWidget(canvas2)

        # 3. 3D Фазовый портрет
        fig3 = Figure(figsize=(8, 8))
        canvas3 = FigureCanvas(fig3)
        ax3 = fig3.add_subplot(111, projection='3d')
        ax3.plot(self.x_data, self.y_data, self.z_data, color='darkgreen', lw=0.8)
        ax3.scatter(self.x_data[0], self.y_data[0], self.z_data[0], color='green', s=50, label='Старт')
        ax3.scatter(self.x_data[-1], self.y_data[-1], self.z_data[-1], color='red', s=80, label='Конец')
        ax3.set_title("3D структура аттрактора Хиндмарша — Роуза")
        ax3.set_xlabel("x")
        ax3.set_ylabel("y")
        ax3.set_zlabel("z")
        self.phase_3d_tab.layout().addWidget(NavigationToolbar(canvas3, self))
        self.phase_3d_tab.layout().addWidget(canvas3)

        threshold = 1.0
        spike_times = []
        for i in range(1, len(self.x_data)):
            if self.x_data[i - 1] < threshold and self.x_data[i] >= threshold:
                spike_times.append(self.t_data[i])

        if len(spike_times) > 1:
            isi_values = np.diff(spike_times)

            # --- 6. Гистограмма ISI ---
            fig_hist = Figure(figsize=(8, 5))
            fig_hist.subplots_adjust(bottom=0.20)
            canvas_hist = FigureCanvas(fig_hist)
            ax_hist = fig_hist.add_subplot(111)
            ax_hist.hist(isi_values, bins=30, color='teal', edgecolor='black', alpha=0.7)
            ax_hist.set_title("Распределение межспайковых интервалов")
            ax_hist.set_xlabel("Интервал (t)")
            ax_hist.set_ylabel("Количество")
            ax_hist.grid(True, alpha=0.2)
            self.isi_hist_tab.layout().addWidget(NavigationToolbar(canvas_hist, self))
            self.isi_hist_tab.layout().addWidget(canvas_hist)

            # --- 7. Последовательность (Динамика) ISI ---
            fig_seq = Figure(figsize=(8, 5))
            fig_seq.subplots_adjust(bottom=0.20)
            canvas_seq = FigureCanvas(fig_seq)
            ax_seq = fig_seq.add_subplot(111)
            ax_seq.plot(range(len(isi_values)), isi_values, 'o-', color='teal', markersize=4, lw=0.5)
            ax_seq.set_title("Изменение интервалов во времени")
            ax_seq.set_xlabel("Номер интервала")
            ax_seq.set_ylabel("Длительность интервала")
            ax_seq.grid(True, alpha=0.3)
            self.isi_seq_tab.layout().addWidget(NavigationToolbar(canvas_seq, self))
            self.isi_seq_tab.layout().addWidget(canvas_seq)
        else:
            for tab in [self.isi_hist_tab, self.isi_seq_tab]:
                label = QLabel("Недостаточно спайков для анализа")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                tab.layout().addWidget(label)

    def save_current_calculation(self):
        if not self.t_data: return False
        if not self.current_calc_id: self.current_calc_id = str(uuid.uuid4())

        calc_data = {
            'id': self.current_calc_id,
            'model_name': 'Модель Хиндмарша — Роуза',
            'a': float(self.a_input.text()), 'b': float(self.b_input.text()),
            'c': float(self.c_input.text()), 'd': float(self.d_input.text()),
            'r': float(self.r_input.text()), 's': float(self.s_input.text()),
            'I': float(self.i_input.text()),
            'timestamp': datetime.now().isoformat(),
            't_data': self.t_data, 'x_data': self.x_data,
            'y_data': self.y_data, 'z_data': self.z_data
        }
        result = save_calculation(calc_data)
        QMessageBox.information(self, "Сохранение", result)
        return True

    def load_calculation_by_id(self, calc_id):
        calc = load_calculation(calc_id)
        if calc:
            self.current_calc_id = calc_id
            self.a_input.setText(str(calc.get('a', '1.0')))
            self.b_input.setText(str(calc.get('b', '3.0')))
            self.c_input.setText(str(calc.get('c', '1.0')))
            self.d_input.setText(str(calc.get('d', '5.0')))
            self.r_input.setText(str(calc.get('r', '0.006')))
            self.s_input.setText(str(calc.get('s', '4.0')))
            self.i_input.setText(str(calc.get('I', '3.1')))
            self.t_data = calc.get('t_data', [])
            self.x_data = calc.get('x_data', [])
            self.y_data = calc.get('y_data', [])
            self.z_data = calc.get('z_data', [])
            if self.t_data: self.plot_graphs()
            return True
        return False