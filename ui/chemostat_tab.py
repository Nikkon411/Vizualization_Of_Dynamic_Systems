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
from mpl_toolkits.mplot3d import Axes3D  # Необходимо для 3D

from core.calculation_thread import CalculationThread
from core.database import save_calculation, load_calculation


class ChemostatTab(QWidget):
    """Вкладка: Модель хемостата (Биореактор)"""

    def __init__(self):
        super().__init__()
        self.t_data, self.s_data, self.x_data = [], [], []
        self.calculation_thread = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Модель хемостата: Динамика микроорганизмов")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form_layout = QFormLayout()

        # Параметры хемостата
        self.d_input = QLineEdit("0.1")  # D
        self.s0_input = QLineEdit("10.0")  # S0
        self.mumax_input = QLineEdit("0.5")  # mu_max
        self.ks_input = QLineEdit("2.0")  # Ks
        self.y_input = QLineEdit("0.6")  # Y

        # Начальные условия
        self.s_init_input = QLineEdit("5.0")
        self.x_init_input = QLineEdit("1.0")
        self.t_max_input = QLineEdit("100")

        form_layout.addRow("Скорость протока D:", self.d_input)
        form_layout.addRow("Субстрат на входе S0:", self.s0_input)
        form_layout.addRow("Макс. рост mu_max:", self.mumax_input)
        form_layout.addRow("Константа Ks:", self.ks_input)
        form_layout.addRow("Выход биомассы Y:", self.y_input)
        form_layout.addRow("Нач. Субстрат S:", self.s_init_input)
        form_layout.addRow("Нач. Биомасса X:", self.x_init_input)
        form_layout.addRow("Время T max:", self.t_max_input)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)

        self.calc_button = QPushButton("Рассчитать")
        self.calc_button.clicked.connect(self.on_calculate)

        self.graph_tabs = QTabWidget()
        self.time_tab = QWidget()
        self.phase_tab = QWidget()

        self.tabs_list = [self.time_tab, self.phase_tab]
        for tab in self.tabs_list:
            tab.setLayout(QVBoxLayout())

        self.graph_tabs.addTab(self.time_tab, "Временная динамика")
        self.graph_tabs.addTab(self.phase_tab, "Фазовый портрет (S-X)")

        layout.addWidget(title)
        layout.addLayout(form_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.calc_button)
        layout.addWidget(self.graph_tabs)
        self.setLayout(layout)

    def on_calculate(self):
        try:
            # Сбор данных из полей ввода
            d = self.d_input.text()
            s0 = self.s0_input.text()
            mu = self.mumax_input.text()
            ks = self.ks_input.text()
            y = self.y_input.text()
            s_init = self.s_init_input.text()
            x_init = self.x_init_input.text()
            t_max = self.t_max_input.text()

            if not all([d, s0, mu, ks, y, s_init, x_init, t_max]):
                QMessageBox.warning(self, "Предупреждение", "Заполните все параметры!")
                return

            self.calc_button.setEnabled(False)
            self.calc_button.setText("⏳ Вычисление...")
            self.progress_bar.setVisible(True)

            # Создаем поток, передавая параметры в порядке: D, S0, mu_max, Ks, Y, S_init, X_init, t_max
            self.calculation_thread = CalculationThread(
                d, s0, mu, ks, y, s_init, x_init, t_max,
                model="chemostat"
            )
            self.calculation_thread.calculation_finished.connect(self.on_finished)
            self.calculation_thread.calculation_error.connect(self.on_error)
            self.calculation_thread.start()

        except Exception as e:
            self.on_error(str(e))

    def on_finished(self, result):
        self.calc_button.setEnabled(True)
        self.calc_button.setText("Рассчитать")
        self.progress_bar.setVisible(False)

        if not result:
            QMessageBox.warning(self, "Ошибка", "Получен пустой результат от Wolfram.")
            return

        # Разбор результата (Wolfram возвращает t, S, X)
        self.t_data = [float(r[0]) for r in result]
        self.s_data = [float(r[1]) for r in result]
        self.x_data = [float(r[2]) for r in result]

        self.plot_graphs()

    def on_error(self, error):
        self.calc_button.setEnabled(True)
        self.calc_button.setText("Рассчитать")
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Ошибка расчета", f"Произошла ошибка: {error}")

    def plot_graphs(self):
        # Очистка старых графиков
        for tab in self.tabs_list:
            layout = tab.layout()
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

        # 1. Временные ряды (S и X)
        fig1 = Figure(figsize=(8, 5))
        fig1.subplots_adjust(bottom=0.20)
        canvas1 = FigureCanvas(fig1)
        ax1 = fig1.add_subplot(111)
        ax1.plot(self.t_data, self.s_data, label='Субстрат (S)', color='blue', lw=2)
        ax1.plot(self.t_data, self.x_data, label='Биомасса (X)', color='green', lw=2)
        ax1.set_title("Переходный процесс в хемостате")
        ax1.set_xlabel("Время (t)")
        ax1.set_ylabel("Концентрация")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        self.time_tab.layout().addWidget(NavigationToolbar(canvas1, self))
        self.time_tab.layout().addWidget(canvas1)

        # 2. Фазовый портрет
        fig2 = Figure(figsize=(6, 6))
        fig2.subplots_adjust(bottom=0.20)
        canvas2 = FigureCanvas(fig2)
        ax2 = fig2.add_subplot(111)
        ax2.plot(self.s_data, self.x_data, color='purple', lw=1.5)
        # Отмечаем начальную точку
        ax2.scatter(self.s_data[0], self.x_data[0], color='red', label='Старт')
        # Отмечаем конечную точку (стационарное состояние)
        ax2.scatter(self.s_data[-1], self.x_data[-1], color='black', marker='x', s=100, label='Устойчивое состояние')

        ax2.set_title("Фазовый портрет: Субстрат - Биомасса")
        ax2.set_xlabel("S (Субстрат)")
        ax2.set_ylabel("X (Микроорганизмы)")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        self.phase_tab.layout().addWidget(NavigationToolbar(canvas2, self))
        self.phase_tab.layout().addWidget(canvas2)