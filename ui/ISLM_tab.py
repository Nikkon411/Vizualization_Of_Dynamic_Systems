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


class ISLMTab(QWidget):
    """Вкладка: Динамическая модель IS-LM (Равновесие товарного и денежного рынков)"""

    def __init__(self):
        super().__init__()
        self.t_data, self.Y_data, self.i_data = [], [], []
        self.dY_dt_data, self.di_dt_data = [], []
        self.calculation_thread = None
        self.current_calc_id = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Макроэкономическая модель IS-LM")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form_layout = QFormLayout()

        # Параметры IS (Товарный рынок)
        self.G_input = QLineEdit("250")  # Увеличили расходы государства
        self.C0_input = QLineEdit("200")  # Люди тратят чуть больше базы
        self.MPC_input = QLineEdit("0.75")  # Нормальная склонность к потреблению
        self.I0_input = QLineEdit("200")  # Бизнес настроен бодро
        self.d_input = QLineEdit("15")  # Бизнес умеренно реагирует на ставку

        # Параметры LM (Денежный рынок)
        self.Ms_input = QLineEdit("500")  # Меньше денег = выше ставка (защита от минуса)
        self.P_input = QLineEdit("1.0")
        self.k_input = QLineEdit("0.35")  # Спрос на деньги умеренный
        self.h_input = QLineEdit("50")  # Плавная реакция рынка

        # Динамика и начальные условия
        self.Y0_input = QLineEdit("1800")  # Начнем с нормального уровня дохода
        self.rate0_input = QLineEdit("6")  # Начнем с высокой ставки
        self.t_max_input = QLineEdit("150")

        form_layout.addRow("Гос. расходы (G):", self.G_input)
        form_layout.addRow("Потребление (C0 + MPC*Y):", self.C0_input)
        form_layout.addRow("Склонность к потр. (MPC):", self.MPC_input)
        form_layout.addRow("Инвестиции (I0):", self.I0_input)
        form_layout.addRow("Предложение денег (Ms):", self.Ms_input)
        form_layout.addRow("Нач. доход (Y₀):", self.Y0_input)
        form_layout.addRow("Нач. ставка (i₀):", self.rate0_input)
        form_layout.addRow("T max:", self.t_max_input)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)

        self.calc_button = QPushButton("Рассчитать")
        self.calc_button.clicked.connect(self.on_calculate)

        self.graph_tabs = QTabWidget()
        self.main_tab = QWidget()  # Основной крест IS-LM
        self.dyn_tab = QWidget()  # Динамика Y и i во времени
        self.inv_tab = QWidget()
        self.money_tab = QWidget()
        self.goods_tab = QWidget()
        self.phase_tab = QWidget()  # Фазовый портрет
        self.elastic_tab = QWidget()  # Эластичность спроса
        self.tabs_list = [self.main_tab, self.dyn_tab, self.inv_tab, self.money_tab, self.goods_tab, self.phase_tab, self.elastic_tab]

        for tab in self.tabs_list:
            tab.setLayout(QVBoxLayout())

        self.graph_tabs.addTab(self.main_tab, "Кривые IS-LM")
        self.graph_tabs.addTab(self.dyn_tab, "Динамика показателей")
        self.graph_tabs.addTab(self.inv_tab, "Рынок инвестиций")
        self.graph_tabs.addTab(self.money_tab, "Рынок денег")
        self.graph_tabs.addTab(self.goods_tab, "Кейнсианский крест")

        self.graph_tabs.addTab(self.phase_tab, "Фазовый портрет")
        self.graph_tabs.addTab(self.elastic_tab, "Эластичность спроса")

        layout.addWidget(title)
        layout.addLayout(form_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.calc_button)
        layout.addWidget(self.graph_tabs)
        self.setLayout(layout)

    def on_calculate(self):
        try:
            # Считываем все поля ввода и конвертируем в float
            g = float(self.G_input.text())
            c0 = float(self.C0_input.text())
            mpc = float(self.MPC_input.text())
            i0_inv = float(self.I0_input.text())
            d = float(self.d_input.text())
            ms = float(self.Ms_input.text())
            p_price = float(self.P_input.text())
            k = float(self.k_input.text())
            h = float(self.h_input.text())
            y_start = float(self.Y0_input.text())
            rate_start = float(self.rate0_input.text())
            t_max = float(self.t_max_input.text())

            self.calc_button.setEnabled(False)
            self.calc_button.setText("⏳ Вычисление в Wolfram...")
            self.progress_bar.setVisible(True)

            # ПЕРЕДАЕМ ПАРАМЕТРЫ ПО ПОРЯДКУ (их ровно 12)
            self.calculation_thread = CalculationThread(
                g, c0, mpc, i0_inv, d, ms, p_price, k, h, y_start, rate_start, t_max,
                model="islm"
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
        self.Y_data = [float(r[1]) for r in result]
        self.i_data = [float(r[2]) for r in result]
        self.dY_dt_data = [float(r[3]) for r in result]
        self.di_dt_data = [float(r[4]) for r in result]
        self.plot_graphs()

    def on_error(self, error):
        self.calc_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Ошибка", f"Крах экономики:\n{error}")

    def plot_graphs(self):
        for tab in self.tabs_list:
            layout = tab.layout()
            while layout.count():
                layout.takeAt(0).widget().deleteLater()

        Y = np.array(self.Y_data)
        i_rate = np.array(self.i_data)
        t = np.array(self.t_data)

        # 1. Сбор параметров
        G = float(self.G_input.text())
        C0 = float(self.C0_input.text())
        mpc = float(self.MPC_input.text())
        I0 = float(self.I0_input.text())
        d = float(self.d_input.text())
        Ms = float(self.Ms_input.text())
        P = float(self.P_input.text())
        k = float(self.k_input.text())
        h = float(self.h_input.text())

        real_money_supply = Ms / P
        money_demand = k * Y - h * i_rate
        investments = I0 - d * i_rate
        consumption = C0 + mpc * Y
        aggregate_demand = consumption + investments + G

        # 2. ОПРЕДЕЛЯЕМ ГЛОБАЛЬНЫЕ ГРАНИЦЫ (FORCE ZOOM OUT)
        # Мы хотим видеть диапазон от 0 до как минимум 3500 по Доходу (Y)
        # И от 0 до как минимум 10-15 по Ставке (i)
        x_min_limit = 0
        x_max_limit = max(np.max(Y) * 1.2, 3500)  # С запасом 20% или минимум 3500
        y_min_limit = min(np.min(i_rate) - 2, 0)  # Позволяем уходить в минус
        y_max_limit = max(np.max(i_rate) + 2, 15)

        # Генерируем статические кривые IS-LM
        Y_static = np.linspace(x_min_limit, x_max_limit, 200)
        IS_static = (C0 + I0 + G - (1 - mpc) * Y_static) / d
        LM_static = (k * Y_static - real_money_supply) / h

        # Генерируем кривые IS-LM во всем этом широком диапазоне
        Y_range = np.linspace(x_min_limit, x_max_limit, 100)
        IS_curve = (C0 + I0 + G - (1 - mpc) * Y_range) / d
        LM_curve = (k * Y_range - Ms / P) / h

        # -------- ГРАФИК 1: IS-LM Кросс --------
        fig1 = Figure(figsize=(7, 4))
        fig1.subplots_adjust(bottom=0.20)
        canvas1 = FigureCanvas(fig1)
        ax1 = fig1.add_subplot(111)

        # Отрисовка линий
        ax1.plot(Y_range, IS_curve, 'r-', label='IS (Товары)', linewidth=2)
        ax1.plot(Y_range, LM_curve, 'b-', label='LM (Деньги)', linewidth=2)
        ax1.plot(Y, i_rate, 'g--', linewidth=2.5, label='Путь к равновесию', alpha=0.9)

        # Точки
        ax1.scatter([Y[0]], [i_rate[0]], color='green', s=80, label='Старт (Y0, i0)', zorder=5)
        ax1.scatter([Y[-1]], [i_rate[-1]], color='black', s=120, label='Точка E (Финал)', zorder=6)

        # ВЫЧИСЛЯЕМ ОПТИМАЛЬНЫЕ ГРАНИЦЫ
        # По X: добавляем 15% отступа слева и справа
        x_range = Y_range[-1] - Y_range[0]
        x_min = Y_range[0] - 1.2 * x_range
        x_max = Y_range[-1] + 1.2 * x_range

        # По Y: используем ваши пределы, но тоже можно добавить отступ
        y_range_data = y_max_limit - y_min_limit
        y_min = y_min_limit - 1.2 * y_range_data
        y_max = y_max_limit + 1.2 * y_range_data

        ax1.set_xlim(x_min, x_max)
        ax1.set_ylim(y_min, y_max)  # или оставьте ваши y_min_limit, y_max_limit

        ax1.set_xlabel("Доход (Y)")
        ax1.set_ylabel("Ставка (i)")
        ax1.set_title("Глобальное равновесие модели IS-LM")
        ax1.legend(loc='upper right')
        ax1.grid(True, which='both', linestyle='--', alpha=0.5)

        self.main_tab.layout().addWidget(NavigationToolbar(canvas1, self))
        self.main_tab.layout().addWidget(canvas1)

        # -------- ГРАФИК 2: Временные ряды (Динамика) --------
        fig2 = Figure(figsize=(7, 4))
        fig2.subplots_adjust(bottom=0.20)
        canvas2 = FigureCanvas(fig2)
        ax2 = fig2.add_subplot(211)
        ax2.plot(t, Y, color='darkgreen', linewidth=2)
        ax2.set_ylabel("Доход (Y)")
        ax2.grid(True, alpha=0.2)

        ax3 = fig2.add_subplot(212)
        ax3.plot(t, i_rate, color='darkblue', linewidth=2)
        ax3.set_ylabel("Ставка (i)")
        ax3.set_xlabel("Время (t)")
        ax3.grid(True, alpha=0.2)

        self.dyn_tab.layout().addWidget(NavigationToolbar(canvas2, self))
        self.dyn_tab.layout().addWidget(canvas2)

        # =========================================================================
        # 3. УПРОЩЕННЫЙ РЫНОК ИНВЕСТИЦИЙ (Убираем базу, оставляем только факт)
        # =========================================================================
        fig3 = Figure(figsize=(7, 4))
        fig3.subplots_adjust(bottom=0.20)
        canvas3 = FigureCanvas(fig3)
        ax4 = fig3.add_subplot(111)

        # Считаем реальные инвестиции в каждый момент времени
        real_inv = I0 - d * i_rate

        ax4.plot(t, real_inv, color='orange', linewidth=2.5, label='Инвестиции бизнеса (I)')

        ax4.set_xlabel("Время t");
        ax4.set_ylabel("Объем I")
        ax4.set_title("Динамика реальных инвестиций")
        ax4.legend(loc='lower right');
        ax4.grid(True, alpha=0.2)

        self.inv_tab.layout().addWidget(NavigationToolbar(canvas3, self));
        self.inv_tab.layout().addWidget(canvas3)

        # =========================================================================
        # 4. УПРОЩЕННЫЙ РЫНОК ДЕНЕГ (Убираем старт/середину, оставляем только ФИНАЛ)
        # =========================================================================
        fig4 = Figure(figsize=(7, 4))
        fig4.subplots_adjust(bottom=0.20)
        canvas4 = FigureCanvas(fig4)
        ax5 = fig4.add_subplot(111)

        M_supply = Ms / P

        # Ось денег
        M_axis = np.linspace(M_supply * 0.5, M_supply * 1.5, 100)

        # Несколько моментов времени
        indices = [0, len(Y) // 2, -1]
        colors = ['gray', 'orange', 'green']
        labels = ['Начало', 'Середина', 'Финал']

        for idx, color, label in zip(indices, colors, labels):
            demand_curve = (k * Y[idx] - M_axis) / h
            ax5.plot(M_axis, demand_curve, color=color, linewidth=2, label=f'L ({label})')

        # Предложение денег
        ax5.axvline(x=M_supply, color='blue', linewidth=3, label='Ms/P')

        # Финальная точка
        ax5.scatter([M_supply], [i_rate[-1]], color='red', s=100, zorder=5)

        ax5.set_xlabel("Деньги (M)")
        ax5.set_ylabel("Ставка i")
        ax5.set_title("Рынок денег (динамика)")
        ax5.legend()
        ax5.grid(True, alpha=0.2)

        self.money_tab.layout().addWidget(NavigationToolbar(canvas4, self));
        self.money_tab.layout().addWidget(canvas4)

        # =========================================================================
        # 5. УПРОЩЕННЫЙ КЕЙНСИАНСКИЙ КРЕСТ (Убираем старт, оставляем только ФИНАЛ)
        # =========================================================================
        fig5 = Figure(figsize=(7, 4))
        fig5.subplots_adjust(bottom=0.20)
        canvas5 = FigureCanvas(fig5)
        ax6 = fig5.add_subplot(111)

        # Линия 45°
        ax6.plot(Y_static, Y_static, color='black', linestyle='--', label='Y = AD')

        # Несколько кривых AD
        indices = [0, len(i_rate) // 2, -1]
        colors = ['gray', 'orange', 'red']
        labels = ['Начало', 'Середина', 'Финал']

        for idx, color, label in zip(indices, colors, labels):
            inv = I0 - d * i_rate[idx]
            AD = C0 + mpc * Y_static + inv + G
            ax6.plot(Y_static, AD, color=color, linewidth=2, label=f'AD ({label})')

        # Финальная точка равновесия
        ax6.scatter([Y[-1]], [Y[-1]], color='black', s=120, zorder=5)

        ax6.set_xlabel("Доход Y")
        ax6.set_ylabel("Спрос AD")
        ax6.set_title("Кейнсианский крест (динамика)")
        ax6.legend()
        ax6.grid(True, alpha=0.2)

        self.goods_tab.layout().addWidget(NavigationToolbar(canvas5, self));
        self.goods_tab.layout().addWidget(canvas5)
        ##################################################################################
        fig6 = Figure(figsize=(7, 4))  # Сделаем квадратным для честности фаз
        fig6.subplots_adjust(bottom=0.20)
        canvas6 = FigureCanvas(fig6)
        ax8 = fig6.add_subplot(111)

        # Получаем производные как массивы
        dY_dt = np.array(self.dY_dt_data)
        di_dt = np.array(self.di_dt_data)

        # Траектория скоростей (Зеленая спираль)
        ax8.plot(dY_dt, di_dt, color='darkgreen', linewidth=2.5, label='Фазовая траектория', alpha=0.8)

        # Точка старта и финала скоростей
        # Финал всегда в (0, 0), когда подстройка завершена.
        ax8.scatter([dY_dt[0]], [di_dt[0]], color='green', s=100, zorder=5, label='Старт')
        ax8.scatter([0], [0], color='black', s=150, zorder=6, label='Равновесие (0,0)')

        # Оси координат (крест через ноль)
        ax8.axhline(y=0, color='black', linewidth=1, linestyle='-')
        ax8.axvline(x=0, color='black', linewidth=1, linestyle='-')

        # Сетка и подписи
        ax8.set_xlabel("Скорость изменения Дохода (dY/dt)", fontsize=7)
        ax8.set_ylabel("Скорость изменения Ставки (di/dt)", fontsize=7)
        ax8.set_title("Фазовый портрет: Устойчивость системы")
        ax8.legend(loc='upper right', fontsize='small')
        ax8.grid(True, which='both', linestyle='--', alpha=0.3)

        self.phase_tab.layout().addWidget(NavigationToolbar(canvas6, self))
        self.phase_tab.layout().addWidget(canvas6)

        # =========================================================================
        # 7. ГРАФИК ЭЛАСТИЧНОСТИ СПРОСА НА ДЕНЬГИ ПО СТАВКЕ
        # =========================================================================
        # Эластичность = % изменения Спроса / % изменения Ставки
        # E_i = (dL/di) * (i/L)
        # В нашей модели L = kY - hi, значит dL/di = -h.
        # E_i = -h * (i_rate / money_demand)

        fig7 = Figure(figsize=(7, 4))
        fig7.subplots_adjust(bottom=0.20)
        canvas7 = FigureCanvas(fig7)
        ax7 = fig7.add_subplot(111)

        # Считаем спрос на деньги в каждый момент времени
        real_money_supply = Ms / P
        L_demand = k * Y - h * i_rate

        # Избегаем деления на ноль (хотя в L деления нет, на всякий случай)
        safe_L = np.where(L_demand == 0, 1e-9, L_demand)

        # Считаем эластичность (она всегда отрицательная, так как i и L ходят в разные стороны)
        elasticity_i = -h * (i_rate / safe_L)

        # Траектория эластичности во времени
        ax7.plot(t, elasticity_i, color='purple', linewidth=2.5, label='Текущая эластичность')

        # Горизонтальная линия -1 (Условная граница эластичности)
        ax7.axhline(y=-1, color='red', linestyle='--', alpha=0.5, label='Граница (-1)')

        # Точка Финала
        ax7.scatter([t[-1]], [elasticity_i[-1]], color='black', s=120, zorder=5, label='Финал (E)')

        # Сетка и подписи
        ax7.set_xlabel("Время (t)", fontsize=11)
        ax7.set_ylabel("Эластичность спроса по ставке (Ei)", fontsize=7)
        ax7.set_title("Эластичность спроса на деньги во времени")
        ax7.legend(loc='lower right', fontsize='small')
        ax7.grid(True, alpha=0.3)

        # По умолчанию экономисты смотрят наEi, которая обычно < 0.
        # Ei > -1 (ближе к 0) - спрос неэластичен (люди не реагируют на ставку).
        # Ei < -1 (дальше от 0) - спрос эластичен (люди сильно реагируют).

        self.elastic_tab.layout().addWidget(NavigationToolbar(canvas7, self))
        self.elastic_tab.layout().addWidget(canvas7)

    # ================= СОХРАНЕНИЕ И ЗАГРУЗКА =================

    def save_current_calculation(self):
        """Сохранение параметров и результатов расчета IS-LM в БД"""
        if not self.t_data or len(self.t_data) == 0:
            QMessageBox.warning(self, "Предупреждение", "Нет данных для сохранения! Сначала проведите расчет.")
            return False

        if not self.current_calc_id:
            self.current_calc_id = str(uuid.uuid4())

        try:
            calc_data = {
                'id': self.current_calc_id,
                'model_name': 'Макроэкономическая модель IS-LM',
                # Параметры ввода
                'G': float(self.G_input.text()),
                'C0': float(self.C0_input.text()),
                'MPC': float(self.MPC_input.text()),
                'I0': float(self.I0_input.text()),
                'd': float(self.d_input.text()),
                'Ms': float(self.Ms_input.text()),
                'P': float(self.P_input.text()),
                'k': float(self.k_input.text()),
                'h': float(self.h_input.text()),
                'Y0': float(self.Y0_input.text()),
                'rate0': float(self.rate0_input.text()),
                't_max': float(self.t_max_input.text()),

                'timestamp': datetime.now().isoformat(),

                # Результаты вычислений
                't_data': [float(v) for v in self.t_data],
                'Y_data': [float(v) for v in self.Y_data],
                'i_data': [float(v) for v in self.i_data],

                'dY_dt_data': [float(v) for v in self.dY_dt_data],
                'di_dt_data': [float(v) for v in self.di_dt_data]
            }

            result = save_calculation(calc_data)
            QMessageBox.information(self, "Сохранение", result)
            return True
        except ValueError:
            QMessageBox.critical(self, "Ошибка", "Проверьте корректность введенных чисел перед сохранением.")
            return False

    def load_calculation_by_id(self, calc_id):
        """Загрузка данных расчета по ID и отрисовка графиков"""
        calc = load_calculation(calc_id)
        if calc:
            self.current_calc_id = calc_id

            # Восстанавливаем поля ввода
            self.G_input.setText(str(calc.get('G', '250')))
            self.C0_input.setText(str(calc.get('C0', '200')))
            self.MPC_input.setText(str(calc.get('MPC', '0.75')))
            self.I0_input.setText(str(calc.get('I0', '200')))
            self.d_input.setText(str(calc.get('d', '15')))
            self.Ms_input.setText(str(calc.get('Ms', '500')))
            self.P_input.setText(str(calc.get('P', '1.0')))
            self.k_input.setText(str(calc.get('k', '0.35')))
            self.h_input.setText(str(calc.get('h', '50')))

            self.Y0_input.setText(str(calc.get('Y0', '1800')))
            self.rate0_input.setText(str(calc.get('rate0', '6')))
            self.t_max_input.setText(str(calc.get('t_max', '100')))

            # Загружаем массивы данных для графиков
            if 't_data' in calc:
                self.t_data = calc['t_data']
                self.Y_data = calc['Y_data']
                self.i_data = calc['i_data']

                self.dY_dt_data = calc.get('dY_dt_data', [])
                self.di_dt_data = calc.get('di_dt_data', [])
                self.plot_graphs()
            return True
        return False