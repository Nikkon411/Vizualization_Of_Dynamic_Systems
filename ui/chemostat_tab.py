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
        self.current_calc_id = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Модель хемостата: Динамика микроорганизмов")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form_layout = QFormLayout()

        # Параметры хемостата
        self.d_input = QLineEdit("0.3")  # D
        self.s0_input = QLineEdit("1.0")  # S0
        self.mumax_input = QLineEdit("4.0")  # mu_max
        self.ks_input = QLineEdit("2.0")  # Ks
        self.y_input = QLineEdit("1.0")  # Y

        # Начальные условия
        self.s_init_input = QLineEdit("0.5")
        self.x_init_input = QLineEdit("0.2")
        self.t_max_input = QLineEdit("50")

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
        # Более надежный способ для Qt6 без вычислений вручную:
        self.graph_tabs.setTabBarAutoHide(False)
        self.graph_tabs.tabBar().setExpanding(True)  # Растягивание
        self.graph_tabs.tabBar().setDocumentMode(True)  # Убирает лишние рамки
        self.time_tab = QWidget()
        self.phase_tab = QWidget()
        self.monod_kinetics_tab = QWidget()
        self.growth_rate_tab = QWidget()
        self.yield_efficiency_tab = QWidget()
        self.uptake_rate_tab = QWidget()
        self.stability_tab = QWidget()

        self.tabs_list = [self.time_tab, self.phase_tab,self.monod_kinetics_tab, self.growth_rate_tab, self.yield_efficiency_tab,
            self.uptake_rate_tab, self.stability_tab]
        for tab in self.tabs_list:
            tab.setLayout(QVBoxLayout())

        self.graph_tabs.addTab(self.time_tab, "Временная динамика")
        self.graph_tabs.addTab(self.phase_tab, "Фазовый портрет (S-X)")
        self.graph_tabs.addTab(self.monod_kinetics_tab, "Кинетика Моно (Теория)")
        self.graph_tabs.addTab(self.growth_rate_tab, "Скорость роста mu(t)")
        self.graph_tabs.addTab(self.yield_efficiency_tab, "Эффективность")
        self.graph_tabs.addTab(self.uptake_rate_tab, "Потребление")
        self.graph_tabs.addTab(self.stability_tab, "Устойчивость")

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

        # ПАРАМЕТРЫ ДЛЯ БИО-АНАЛИЗА
        mu_max = float(self.mumax_input.text())
        ks = float(self.ks_input.text())
        d_rate = float(self.d_input.text())
        y_const = float(self.y_input.text())
        s0_in = float(self.s0_input.text())

        # Расчет mu(t) на основе полученных данных S
        s_arr = np.array(self.s_data)
        mu_t = mu_max * (s_arr / (ks + s_arr))
        x_arr = np.array(self.x_data)
        uptake_t = (1 / y_const) * mu_t * x_arr

        # --- 3. ВКЛАДКА: КИНЕТИКА МОНО (Теоретический график) ---
        fig3 = Figure(figsize=(7, 5))
        fig3.subplots_adjust(bottom=0.20)
        canvas3 = FigureCanvas(fig3)
        ax3 = fig3.add_subplot(111)

        # Рисуем кривую Моно
        s_range = np.linspace(0, max(self.s_data) * 1.5 if self.s_data else 20, 100)
        mu_range = mu_max * (s_range / (ks + s_range))
        ax3.plot(s_range, mu_range, color='red', lw=2, label=r'$\mu = \mu_{max} \cdot S / (K_s + S)$')

        # Линия скорости протока (критическая точка)
        ax3.axhline(y=d_rate, color='black', linestyle='--', label=f'Скорость протока D={d_rate}')

        ax3.set_title("Теоретическая зависимость скорости роста от субстрата")
        ax3.set_xlabel("Концентрация субстрата (S)")
        ax3.set_ylabel(r"Удельная скорость роста ($\mu$)")
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        self.monod_kinetics_tab.layout().addWidget(NavigationToolbar(canvas3, self))
        self.monod_kinetics_tab.layout().addWidget(canvas3)

        # --- 4. ВКЛАДКА: ДИНАМИКА СКОРОСТИ РОСТА mu(t) ---
        fig4 = Figure(figsize=(7, 5))
        fig4.subplots_adjust(bottom=0.20)
        canvas4 = FigureCanvas(fig4)
        ax4 = fig4.add_subplot(111)

        ax4.plot(self.t_data, mu_t, color='orange', lw=2, label=r'Текущая $\mu(t)$')
        ax4.axhline(y=d_rate, color='black', linestyle='--', label='Уровень стабилизации (D)')

        ax4.set_title("Изменение скорости роста в процессе культивирования")
        ax4.set_xlabel("Время (t)")
        ax4.set_ylabel(r"Скорость роста $\mu$ (1/ч)")
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        self.growth_rate_tab.layout().addWidget(NavigationToolbar(canvas4, self))
        self.growth_rate_tab.layout().addWidget(canvas4)

        # --- 5. ЭФФЕКТИВНОСТЬ (YIELD) ---
        fig5 = Figure(figsize=(7, 4))
        fig5.subplots_adjust(bottom=0.20)
        canvas5 = FigureCanvas(fig5)
        ax5 = fig5.add_subplot(111)
        # Эффективность как отношение прироста биомассы к потребленному субстрату
        delta_s = np.maximum(0.001, s0_in - s_arr)
        yield_real = x_arr / delta_s
        ax5.plot(self.t_data, yield_real, color='teal', lw=2)
        ax5.axhline(y=y_const, color='red', ls='--', label='Теор. выход Y')
        ax5.set_title("Экономический коэффициент в динамике")
        ax5.set_xlabel("Время")
        ax5.set_ylabel("Выход биомассы на ед. субстрата", fontsize=9)
        ax5.legend()
        self.yield_efficiency_tab.layout().addWidget(NavigationToolbar(canvas5, self))
        self.yield_efficiency_tab.layout().addWidget(canvas5)

        # --- 6. ПОТРЕБЛЕНИЕ СУБСТРАТА (UPTAKE RATE) ---
        fig6 = Figure(figsize=(7, 4))
        fig6.subplots_adjust(bottom=0.20)
        canvas6 = FigureCanvas(fig6)
        ax6 = fig6.add_subplot(111)
        ax6.fill_between(self.t_data, uptake_t, color='blue', alpha=0.3)
        ax6.plot(self.t_data, uptake_t, color='blue', lw=2)
        ax6.set_title("Скорость потребления питания популяцией")
        ax6.set_xlabel("Время")
        ax6.set_ylabel("Потребление (г/л в час)")
        self.uptake_rate_tab.layout().addWidget(NavigationToolbar(canvas6, self))
        self.uptake_rate_tab.layout().addWidget(canvas6)

        # --- 7. КАРТА УСТОЙЧИВОСТИ (БИФУРКАЦИОННЫЙ АНАЛИЗ) ---
        fig7 = Figure(figsize=(7, 4))
        fig7.subplots_adjust(bottom=0.20)
        canvas7 = FigureCanvas(fig7)
        ax7 = fig7.add_subplot(111)

        # Генерируем диапазон скоростей протока D
        d_range = np.linspace(0.01, mu_max * 0.99, 100)
        s_star = (ks * d_range) / (mu_max - d_range)
        x_star = np.maximum(0, y_const * (s0_in - s_star))

        ax7.plot(d_range, x_star, color='darkgreen', lw=3, label='Стационарная биомасса X*')
        ax7.axvline(x=d_rate, color='orange', ls='-', label='Текущая рабочая точка')

        # Точка вымывания (Washout)
        d_washout = (mu_max * s0_in) / (ks + s0_in)
        ax7.axvline(x=d_washout, color='red', ls=':', label='Точка вымывания (Washout)')

        ax7.set_title("Зависимость выхода продукта от скорости протока")
        ax7.set_xlabel("Скорость протока D")
        ax7.set_ylabel("Стабильная концентрация X")
        ax7.legend()
        self.stability_tab.layout().addWidget(NavigationToolbar(canvas7, self))
        self.stability_tab.layout().addWidget(canvas7)


    def save_current_calculation(self):
        """Сохранение результатов расчета хемостата в БД"""
        if not self.t_data:
            QMessageBox.warning(self, "Ошибка", "Нет данных для сохранения. Сначала выполните расчет.")
            return False

        if not self.current_calc_id:
            self.current_calc_id = str(uuid.uuid4())

        calc_data = {
            'id': self.current_calc_id,
            'model_name': 'Модель хемостата',
            # Параметры модели
            'd_rate': float(self.d_input.text()),
            's0_in': float(self.s0_input.text()),
            'mu_max': float(self.mumax_input.text()),
            'ks': float(self.ks_input.text()),
            'y_yield': float(self.y_input.text()),
            # Начальные условия
            's_init': float(self.s_init_input.text()),
            'x_init': float(self.x_init_input.text()),
            't_max': float(self.t_max_input.text()),
            # Метаданные
            'timestamp': datetime.now().isoformat(),
            # Массивы данных (результаты)
            't_data': self.t_data,
            's_data': self.s_data,
            'x_data': self.x_data
        }

        result = save_calculation(calc_data)
        QMessageBox.information(self, "Сохранение", result)
        return True


    def load_calculation_by_id(self, calc_id):
        """Загрузка расчета хемостата из БД по ID"""
        calc = load_calculation(calc_id)
        if calc:
            self.current_calc_id = calc_id

            # Восстанавливаем значения в полях ввода
            self.d_input.setText(str(calc.get('d_rate', '0.3')))
            self.s0_input.setText(str(calc.get('s0_in', '1.0')))
            self.mumax_input.setText(str(calc.get('mu_max', '4.0')))
            self.ks_input.setText(str(calc.get('ks', '2.0')))
            self.y_input.setText(str(calc.get('y_yield', '1.0')))
            self.s_init_input.setText(str(calc.get('s_init', '0.5')))
            self.x_init_input.setText(str(calc.get('x_init', '0.2')))
            self.t_max_input.setText(str(calc.get('t_max', '50')))

            # Загружаем массивы данных решения
            self.t_data = calc.get('t_data', [])
            self.s_data = calc.get('s_data', [])
            self.x_data = calc.get('x_data', [])

            if self.t_data:
                self.plot_graphs()

            return True
        return False