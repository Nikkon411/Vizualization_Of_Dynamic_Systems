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

from core.calculation_thread import CalculationThread
from core.database import save_calculation, load_calculation


class VanDerPolTab(QWidget):
    """Вкладка: Осциллятор Ван дер Поля"""

    def __init__(self):
        super().__init__()
        self.t_data, self.x_data, self.y_data = [], [], []
        self.calculation_thread = None
        self.current_calc_id = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Осциллятор Ван дер Поля: Предельные циклы")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form_layout = QFormLayout()
        self.mu_input = QLineEdit("1.5")
        self.x0_input = QLineEdit("0.5")
        self.y0_input = QLineEdit("0.0")
        self.t_max_input = QLineEdit("50")

        form_layout.addRow("Параметр мю (mu):", self.mu_input)
        form_layout.addRow("Нач. положение x:", self.x0_input)
        form_layout.addRow("Нач. скорость y:", self.y0_input)
        form_layout.addRow("Время T max:", self.t_max_input)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)

        self.calc_button = QPushButton("Рассчитать осциллятор")  # ← НАДПИСЬ КАК ВЕЗДЕ
        self.calc_button.clicked.connect(self.on_calculate)     # ← ПОДКЛЮЧАЕМ СИГНАЛ

        self.graph_tabs = QTabWidget()
        self.graph_tabs.tabBar().setExpanding(True)
        self.graph_tabs.tabBar().setDocumentMode(True)

        self.time_tab = QWidget()
        self.phase_tab = QWidget()
        self.energy_tab = QWidget()
        self.fft_tab = QWidget()
        self.nullclines_tab = QWidget()
        self.poincare_tab = QWidget()

        self.tabs_list = [self.time_tab, self.phase_tab, self.energy_tab, self.fft_tab, self.nullclines_tab, self.poincare_tab]
        for tab in self.tabs_list:
            tab.setLayout(QVBoxLayout())

        self.graph_tabs.addTab(self.time_tab, "Осцилляции x(t)")
        self.graph_tabs.addTab(self.phase_tab, "Предельный цикл")
        self.graph_tabs.addTab(self.energy_tab, "Энергия системы")
        self.graph_tabs.addTab(self.fft_tab, "Амплитудный спектр")
        self.graph_tabs.addTab(self.nullclines_tab, "Нульклины")  # Добавили
        self.graph_tabs.addTab(self.poincare_tab, "Карта возврата")  # Добавили

        layout.addWidget(title)
        layout.addLayout(form_layout)
        layout.addWidget(self.progress_bar)      # ← ДОБАВЛЯЕМ ПОЛОСКУ ПРОГРЕССА
        layout.addWidget(self.calc_button)
        layout.addWidget(self.graph_tabs)
        self.setLayout(layout)

    def on_calculate(self):
        try:
            params = [
                self.mu_input.text(),
                self.x0_input.text(),
                self.y0_input.text(),
                self.t_max_input.text()
            ]

            if not all(params):
                QMessageBox.warning(self, "Предупреждение", "Заполните все параметры!")
                return

            self.calc_button.setEnabled(False)
            self.progress_bar.setVisible(True)

            self.calculation_thread = CalculationThread(*params, model="vanderpol")
            self.calculation_thread.calculation_finished.connect(self.on_finished)
            self.calculation_thread.calculation_error.connect(self.on_error)
            self.calculation_thread.start()
        except Exception as e:
            self.on_error(str(e))

    def on_finished(self, result):
        self.calc_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        if not result:
            return

        self.t_data = [float(r[0]) for r in result]
        self.x_data = [float(r[1]) for r in result]
        self.y_data = [float(r[2]) for r in result]

        self.plot_graphs()

    def on_error(self, error):
        self.calc_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Ошибка", f"Ошибка: {error}")

    def plot_graphs(self):
        # Очистка старых графиков
        for tab in self.tabs_list:
            while tab.layout().count():
                child = tab.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

        # 1. График осцилляций x(t)
        fig1 = Figure(figsize=(8, 4))
        canvas1 = FigureCanvas(fig1)
        ax1 = fig1.add_subplot(111)
        ax1.plot(self.t_data, self.x_data, color='royalblue', lw=1.5)
        ax1.set_title("Временная зависимость x(t)")
        ax1.set_xlabel("t")
        ax1.set_ylabel("x")
        ax1.grid(True, alpha=0.3)
        self.time_tab.layout().addWidget(NavigationToolbar(canvas1, self))
        self.time_tab.layout().addWidget(canvas1)

        # 2. Фазовый портрет (Предельный цикл)
        fig2 = Figure(figsize=(6, 6))
        canvas2 = FigureCanvas(fig2)
        ax2 = fig2.add_subplot(111)
        ax2.plot(self.x_data, self.y_data, color='darkviolet', lw=1)
        ax2.scatter(self.x_data[0], self.y_data[0], color='red', label='Старт', s=40, zorder=5)
        ax2.set_title("Фазовая плоскость (x vs y)")
        ax2.set_xlabel("x")
        ax2.set_ylabel("y")
        ax2.grid(True, alpha=0.3)
        self.phase_tab.layout().addWidget(NavigationToolbar(canvas2, self))
        self.phase_tab.layout().addWidget(canvas2)

        # 3. Энергия системы E = 0.5 * (x^2 + y^2)
        energy = 0.5 * (np.array(self.x_data) ** 2 + np.array(self.y_data) ** 2)

        fig3 = Figure(figsize=(8, 4))
        canvas3 = FigureCanvas(fig3)
        ax3 = fig3.add_subplot(111)
        ax3.fill_between(self.t_data, energy, color='seagreen', alpha=0.3)
        ax3.plot(self.t_data, energy, color='seagreen', lw=1.5)
        ax3.set_title("Изменение квази-энергии во времени")
        ax3.set_xlabel("t")
        ax3.set_ylabel("E")
        ax3.grid(True, alpha=0.3)
        self.energy_tab.layout().addWidget(NavigationToolbar(canvas3, self))
        self.energy_tab.layout().addWidget(canvas3)

        # Спектральный анализ x(t)
        n = len(self.x_data)
        freq = np.fft.rfftfreq(n, d=(self.t_data[1] - self.t_data[0]))
        mag = np.abs(np.fft.rfft(self.x_data))

        fig4 = Figure(figsize=(8, 4))
        canvas4 = FigureCanvas(fig4)
        ax4 = fig4.add_subplot(111)
        ax4.semilogy(freq, mag, color='firebrick')
        ax4.set_title("Амплитудный спектр (FFT)")
        ax4.set_xlabel("Частота")
        ax4.set_ylabel("Амплитуда")
        ax4.grid(True, which='both', alpha=0.3)
        self.fft_tab.layout().addWidget(NavigationToolbar(canvas4, self))
        self.fft_tab.layout().addWidget(canvas4)

        # --- НОВЫЙ ГРАФИК 1: Нульклины ---
        mu = float(self.mu_input.text())
        fig5 = Figure(figsize=(6, 6))
        canvas5 = FigureCanvas(fig5)
        ax5 = fig5.add_subplot(111)

        # Траектория
        ax5.plot(self.x_data, self.y_data, color='darkviolet', lw=0.8, alpha=0.6, label='Траектория')

        # Расчет нульклин
        # Ограничим x_range, чтобы избежать бесконечностей при делении на mu*(1-x^2)
        x_max = max(abs(min(self.x_data)), abs(max(self.x_data))) + 0.5
        x_range = np.linspace(-x_max, x_max, 500)

        # Нульклина x' = y (или y=0)
        ax5.axhline(0, color='gray', linestyle='--', alpha=0.5, label="Нульклина x' = 0 (y=0)")

        # Нульклина y' = mu*(1-x^2)*y - x (или y = x / (mu*(1-x^2)))
        # Чтобы избежать разрывов при делении на ноль, используем маскирование
        with np.errstate(divide='ignore', invalid='ignore'):
            y_nullcline = x_range / (mu * (1 - x_range ** 2))
            # Маскируем экстремальные значения для красивой отрисовки
            y_nullcline[np.abs(y_nullcline) > 10] = np.nan

        ax5.plot(x_range, y_nullcline, color='orange', linestyle='--', lw=2, label="Нульклина y' = 0")

        ax5.set_title(f"Геометрия фазовой плоскости (mu={mu})")
        ax5.set_xlabel("x")
        ax5.set_ylabel("y")
        ax5.grid(True, alpha=0.3)
        ax5.legend(loc='best', fontsize='small')

        self.nullclines_tab.layout().addWidget(NavigationToolbar(canvas5, self))
        self.nullclines_tab.layout().addWidget(canvas5)

        # --- НОВЫЙ ГРАФИК 2: Карта возврата (Сечение Пуанкаре) ---
        # Суть: фиксируем точки x[n] в моменты пересечения плоскости y=0 сверху вниз (y становится < 0)
        poincare_points = []
        for i in range(1, len(self.y_data)):
            # Условие пересечения оси y=0 сверху вниз
            if self.y_data[i - 1] > 0 and self.y_data[i] <= 0:
                # Точное нахождение x методом линейной интерполяции
                t_crossing = self.t_data[i - 1] + (0 - self.y_data[i - 1]) * (self.t_data[i] - self.t_data[i - 1]) / (
                            self.y_data[i] - self.y_data[i - 1])
                x_crossing = self.x_data[i - 1] + (t_crossing - self.t_data[i - 1]) * (
                            self.x_data[i] - self.x_data[i - 1]) / (self.t_data[i] - self.t_data[i - 1])
                poincare_points.append(x_crossing)

        fig6 = Figure(figsize=(8, 6))
        canvas6 = FigureCanvas(fig6)
        ax6 = fig6.add_subplot(111)

        if len(poincare_points) > 2:
            # Карта возврата: x_{n+1} как функция от x_n
            xn = poincare_points[:-1]
            x_next = poincare_points[1:]

            # Точки пересечений
            ax6.scatter(xn, x_next, color='firebrick', s=20, edgecolors='black', label='Точки пересечения')

            # Линия x_{n+1} = x_n (диагональ)
            axis_limit = max(abs(min(poincare_points)), abs(max(poincare_points))) + 0.2
            diag = np.linspace(-axis_limit, axis_limit, 100)
            ax6.plot(diag, diag, color='gray', linestyle='--', alpha=0.5, label='x_{n+1} = x_n')

            # Визуализация сходимости (паутинная диаграмма)
            # Для простоты просто соединим точки последовательно, чтобы показать ритм
            ax6.plot(xn, x_next, color='firebrick', lw=0.5, alpha=0.3)

            ax6.set_xlim(-axis_limit, axis_limit)
            ax6.set_ylim(-axis_limit, axis_limit)
            ax6.set_title("Карта возврата (Сечение Пуанкаре: y=0, y'<0)")
            ax6.set_xlabel("x_n (n-ое пересечение)")
            ax6.set_ylabel("x_{n+1} (след. пересечение)")
            ax6.grid(True, alpha=0.3)
            ax6.legend(loc='best', fontsize='small')

        else:
            # Мало точек
            label = QLabel("Недостаточно точек пересечения для карты возврата\n(попробуйте увеличить T max)")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.poincare_tab.layout().addWidget(label)
            # Чтобы избежать пустых FigureCanvas, добавим "заглушку"
            fig6.suptitle("Недостаточно данных")

        self.poincare_tab.layout().addWidget(NavigationToolbar(canvas6, self))
        self.poincare_tab.layout().addWidget(canvas6)

    def save_current_calculation(self):
        if not self.t_data:
            return False
        if not self.current_calc_id:
            self.current_calc_id = str(uuid.uuid4())

        calc_data = {
            'id': self.current_calc_id,
            'model_name': 'Осциллятор Ван дер Поля',
            'mu': float(self.mu_input.text()),
            'x0': float(self.x0_input.text()),
            'y0': float(self.y0_input.text()),
            'timestamp': datetime.now().isoformat(),
            't_data': self.t_data,
            'x_data': self.x_data,
            'y_data': self.y_data
        }
        result = save_calculation(calc_data)
        QMessageBox.information(self, "Сохранение", result)
        return True

    def load_calculation_by_id(self, calc_id):
        calc = load_calculation(calc_id)
        if calc:
            self.current_calc_id = calc_id
            self.mu_input.setText(str(calc.get('mu', '1.5')))
            self.x0_input.setText(str(calc.get('x0', '0.5')))
            self.y0_input.setText(str(calc.get('y0', '0.0')))
            self.t_data = calc.get('t_data', [])
            self.x_data = calc.get('x_data', [])
            self.y_data = calc.get('y_data', [])
            if self.t_data:
                self.plot_graphs()
            return True
        return False