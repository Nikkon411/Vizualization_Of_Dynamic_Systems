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


class LorenzTab(QWidget):
    """Вкладка: Аттрактор Лоренца (Детерминированный хаос)"""

    def __init__(self):
        super().__init__()
        self.t_data, self.x_data, self.y_data, self.z_data = [], [], [], []
        self.calculation_thread = None
        self.current_calc_id = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Система Лоренца: Модель атмосферного хаоса")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form_layout = QFormLayout()

        # Параметры Лоренца (стандартные для хаоса: 10, 28, 2.66)
        self.sigma_input = QLineEdit("10.0")
        self.rho_input = QLineEdit("28.0")
        self.beta_input = QLineEdit("2.66")

        # Начальные условия
        self.x0_input = QLineEdit("1.0")
        self.y0_input = QLineEdit("1.0")
        self.z0_input = QLineEdit("1.0")
        self.t_max_input = QLineEdit("50")

        form_layout.addRow("Sigma (σ - число Прандтля):", self.sigma_input)
        form_layout.addRow("Rho (ρ - число Рэлея):", self.rho_input)
        form_layout.addRow("Beta (β - геометрия):", self.beta_input)
        form_layout.addRow("Нач. X:", self.x0_input)
        form_layout.addRow("Нач. Y:", self.y0_input)
        form_layout.addRow("Нач. Z:", self.z0_input)
        form_layout.addRow("T max (длительность):", self.t_max_input)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)

        self.calc_button = QPushButton("Рассчитать")
        self.calc_button.clicked.connect(self.on_calculate)

        self.graph_tabs = QTabWidget()
        self.time_tab = QWidget()
        self.phase_tab = QWidget() # 3D аттрактор
        self.butterfly_tab = QWidget()

        self.tabs_list = [self.time_tab, self.phase_tab,self.butterfly_tab]
        for tab in self.tabs_list:
            tab.setLayout(QVBoxLayout())

        self.graph_tabs.addTab(self.time_tab, "Временные ряды (X, Y, Z)")
        self.graph_tabs.addTab(self.phase_tab, "3D Фазовый портрет (Аттрактор)")
        self.graph_tabs.addTab(self.butterfly_tab, "Эффект бабочки")

        layout.addWidget(title)
        layout.addLayout(form_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.calc_button)
        layout.addWidget(self.graph_tabs)
        self.setLayout(layout)

    def on_calculate(self):
        try:
            # Вытаскиваем значения из полей ввода
            sig = self.sigma_input.text()
            rho = self.rho_input.text()
            bet = self.beta_input.text()
            x0 = self.x0_input.text()
            y0 = self.y0_input.text()
            z0 = self.z0_input.text()
            t_max = self.t_max_input.text()

            # Проверка на заполненность
            if not all([sig, rho, bet, x0, y0, z0, t_max]):
                QMessageBox.warning(self, "Предупреждение", "Заполните все поля!")
                return

            self.calc_button.setEnabled(False)
            self.calc_button.setText("⏳ Вычисление...")
            self.progress_bar.setVisible(True)

            self.calculation_thread = CalculationThread(
                sig, rho, bet, x0, y0, z0, t_max,
                model="lorenz"
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

        self.t_data = [float(r[0]) for r in result]
        self.x_data = [float(r[1]) for r in result]
        self.y_data = [float(r[2]) for r in result]
        self.z_data = [float(r[3]) for r in result]

        self.diff_data = [float(r[4]) for r in result]

        self.plot_graphs()

    def on_error(self, error):
        self.calc_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Ошибка: \n{error}")

    def plot_graphs(self):
        for tab in self.tabs_list:
            layout = tab.layout()
            while layout.count():
                layout.takeAt(0).widget().deleteLater()

        # 1. Временные ряды
        fig1 = Figure(figsize=(8, 5))
        fig1.subplots_adjust(bottom=0.20)
        canvas1 = FigureCanvas(fig1)
        ax1 = fig1.add_subplot(111)
        ax1.plot(self.t_data, self.x_data, label='X(t)', alpha=0.8)
        ax1.plot(self.t_data, self.y_data, label='Y(t)', alpha=0.8)
        ax1.plot(self.t_data, self.z_data, label='Z(t)', alpha=0.8)
        ax1.set_title("Динамика переменных во времени")
        ax1.set_xlabel("Время")
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        self.time_tab.layout().addWidget(NavigationToolbar(canvas1, self))
        self.time_tab.layout().addWidget(canvas1)

        # 2. 3D Аттрактор
        fig2 = Figure(figsize=(8, 8))
        canvas2 = FigureCanvas(fig2)
        ax2 = fig2.add_subplot(111, projection='3d')

        # Рисуем саму "бабочку"
        ax2.plot(self.x_data, self.y_data, self.z_data, lw=0.5, color='darkblue')

        # Точки старта и финала
        ax2.scatter(self.x_data[0], self.y_data[0], self.z_data[0], color='green', s=50, label='Старт')
        ax2.scatter(self.x_data[-1], self.y_data[-1], self.z_data[-1], color='red', s=50, label='Финал')

        ax2.set_xlabel("X")
        ax2.set_ylabel("Y")
        ax2.set_zlabel("Z")
        ax2.set_title("Фазовая траектория (Аттрактор Лоренца)")
        ax2.legend()

        self.phase_tab.layout().addWidget(NavigationToolbar(canvas2, self))
        self.phase_tab.layout().addWidget(canvas2)

        # ГРАФИК ЭФФЕКТА БАБОЧКИ
        fig3 = Figure(figsize=(7, 4))
        fig3.subplots_adjust(bottom=0.20)
        canvas3 = FigureCanvas(fig3)
        ax3 = fig3.add_subplot(111)

        # Используем логарифмическую шкалу по Y, так как разница растет экспоненциально
        ax3.semilogy(self.t_data, self.diff_data, color='red', lw=1.5)

        ax3.set_title("Эффект бабочки: Расхождение траекторий (|X1 - X2|)")
        ax3.set_xlabel("Время (t)")
        ax3.set_ylabel("Разность (log масштаб)")
        ax3.grid(True, which="both", ls="--", alpha=0.5)

        # Добавляем пояснение
        ax3.text(0.05, 0.95, "Начальное отклонение: 0.00001", transform=ax3.transAxes,
                 verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.5))

        self.butterfly_tab.layout().addWidget(NavigationToolbar(canvas3, self))
        self.butterfly_tab.layout().addWidget(canvas3)

    def save_current_calculation(self):
        if not self.t_data: return False
        if not self.current_calc_id: self.current_calc_id = str(uuid.uuid4())

        calc_data = {
            'id': self.current_calc_id,
            'model_name': 'Система Лоренца',
            'sigma': float(self.sigma_input.text()),
            'rho': float(self.rho_input.text()),
            'beta': float(self.beta_input.text()),
            'x0': float(self.x0_input.text()),
            'y0': float(self.y0_input.text()),
            'z0': float(self.z0_input.text()),
            't_max': float(self.t_max_input.text()),
            'timestamp': datetime.now().isoformat(),
            't_data': self.t_data,
            'x_data': self.x_data,
            'y_data': self.y_data,
            'z_data': self.z_data,
            'diff_data': self.diff_data  # <-- Сохраняем разность для бабочки
        }
        result = save_calculation(calc_data)
        QMessageBox.information(self, "Сохранение", result)
        return True

    def load_calculation_by_id(self, calc_id):
        calc = load_calculation(calc_id)
        if calc:
            self.sigma_input.setText(str(calc.get('sigma', '10.0')))
            self.rho_input.setText(str(calc.get('rho', '28.0')))
            self.beta_input.setText(str(calc.get('beta', '2.66')))
            self.x0_input.setText(str(calc.get('x0', '1.0')))
            self.y0_input.setText(str(calc.get('y0', '1.0')))
            self.z0_input.setText(str(calc.get('z0', '1.0')))
            self.t_max_input.setText(str(calc.get('t_max', '50')))

            # Загружаем массивы данных
            if 't_data' in calc:
                self.t_data = calc['t_data']
                self.x_data = calc['x_data']
                self.y_data = calc['y_data']
                self.z_data = calc['z_data']
                # Если в старых записях нет diff_data, создаем пустой список во избежание ошибок
                self.diff_data = calc['diff_data']

                self.plot_graphs()
            return True
        return False