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


class SIRTab(QWidget):
    """Вкладка: SEIR модель эпидемии (Susceptible-Exposed-Infected-Recovered)"""

    def __init__(self):
        super().__init__()

        self.t_data = []
        self.S_data = []
        self.E_data = []
        self.I_data = []
        self.R_data = []

        self.calculation_thread = None
        self.current_calc_id = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("Модель эпидемии SEIR")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form_layout = QFormLayout()

        # Коэффициенты
        self.beta_input = QLineEdit("0.8")  # Заражение
        self.alpha_input = QLineEdit("0.2")  # Инкубационный переход
        self.gamma_input = QLineEdit("0.1")# Выздоровление
        self.mu_input = QLineEdit("0.02")
        self.t_max_input = QLineEdit("100")

        # Начальные условия (в долях от единицы)
        self.S0_input = QLineEdit("0.98")
        self.E0_input = QLineEdit("0.01")
        self.I0_input = QLineEdit("0.01")
        self.R0_input = QLineEdit("0.0")

        form_layout.addRow("β (скорость заражения):", self.beta_input)
        form_layout.addRow("α (скорость проявления, 1/инкуб.):", self.alpha_input)
        form_layout.addRow("γ (скорость выздоровления):", self.gamma_input)
        form_layout.addRow("μ (коэффициент летальности):", self.mu_input)
        form_layout.addRow("T max (время расчета):", self.t_max_input)  # Добавляем в форму
        form_layout.addRow("S₀ (восприимчивые):", self.S0_input)
        form_layout.addRow("E₀ (латентные/контактные):", self.E0_input)
        form_layout.addRow("I₀ (инфицированные):", self.I0_input)
        form_layout.addRow("R₀ (выздоровевшие):", self.R0_input)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)

        self.calc_button = QPushButton("Рассчитать")
        self.calc_button.clicked.connect(self.on_calculate)

        self.graph_tabs = QTabWidget()

        self.time_tab = QWidget()
        self.phase_tab = QWidget()
        self.area_tab = QWidget()
        self.rt_tab = QWidget()
        self.incidence_tab = QWidget()
        self.death_tab = QWidget()
        self.growth_tab = QWidget()
        self.stats_tab = QWidget()


        self.tabs_list = [self.time_tab, self.phase_tab, self.area_tab, self.rt_tab, self.incidence_tab,self.death_tab,self.growth_tab,self.stats_tab]

        for tab in self.tabs_list:
            tab.setLayout(QVBoxLayout())

        self.graph_tabs.addTab(self.time_tab, "Линейный график")
        self.graph_tabs.addTab(self.area_tab, "Распределение населения")  # Стековый график
        self.graph_tabs.addTab(self.phase_tab, "Фазовый портрет (E vs I)")
        self.graph_tabs.addTab(self.rt_tab, "Эффективное репродуктивное число")
        self.graph_tabs.addTab(self.growth_tab, "Темп роста")
        self.graph_tabs.addTab(self.incidence_tab, "Новые случаи")
        self.graph_tabs.addTab(self.death_tab, "Летальность")
        self.graph_tabs.addTab(self.stats_tab, "Итог")

        layout.addWidget(title)
        layout.addLayout(form_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.calc_button)
        layout.addWidget(self.graph_tabs)

        self.setLayout(layout)

    def on_calculate(self):
        try:
            beta = self.beta_input.text()
            alpha = self.alpha_input.text()
            gamma = self.gamma_input.text()
            t_max = self.t_max_input.text()
            S0 = self.S0_input.text()
            E0 = self.E0_input.text()
            I0 = self.I0_input.text()
            R0 = self.R0_input.text()

            self.calc_button.setEnabled(False)
            self.calc_button.setText("⏳ Вычисление в Wolfram...")
            self.progress_bar.setVisible(True)

            self.calculation_thread = CalculationThread(
                beta, alpha, gamma, S0, E0, I0, R0, t_max,
                model="seir"  # Вызываем обновленную модель
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
        QMessageBox.critical(self, "Ошибка", f"Не удалось выполнить расчет:\n{error}")

    def on_finished(self, result):
        self.calc_button.setEnabled(True)
        self.calc_button.setText("Рассчитать")
        self.progress_bar.setVisible(False)

        # Парсинг 5 колонок из Wolfram (t, S, E, I, R)
        self.t_data = [float(r[0]) for r in result]
        self.S_data = [float(r[1]) for r in result]
        self.E_data = [float(r[2]) for r in result]
        self.I_data = [float(r[3]) for r in result]
        self.R_data = [float(r[4]) for r in result]

        self.current_calc_id = None
        self.plot_graphs()

    def plot_graphs(self):
        # Очистка всех вкладок (используем ваш список self.tabs_list)
        for tab in self.tabs_list:
            layout = tab.layout()
            while layout.count():
                item = layout.takeAt(0)
                if item.widget(): item.widget().deleteLater()

        t = np.array(self.t_data)
        S = np.array(self.S_data)
        E = np.array(self.E_data)
        I = np.array(self.I_data)
        R = np.array(self.R_data)

        mu = float(self.mu_input.text())

        Deaths = R * mu
        Recovered_Actual = R * (1 - mu)

        growth_rate = np.diff(I) / I[:-1] * 100
        growth_rate = np.insert(growth_rate, 0, 0)  # Добавляем 0 в начало для соответствия размеру t

        beta = float(self.beta_input.text())
        alpha = float(self.alpha_input.text())
        gamma = float(self.gamma_input.text())

        # 1. Расчет Rt = (beta * S) / gamma
        Rt = (beta * S) / gamma

        # 2. Расчет новых случаев (Incidence)
        # Это скорость перехода из E в I: dI_new = alpha * E
        incidence = alpha * E

        # 1. Расчет ключевых точек для статистики
        idx_peak = np.argmax(I)
        t_peak = t[idx_peak]
        i_max = I[idx_peak]
        total_affected = (1 - S[-1]) * 100  # % тех, кто столкнулся с вирусом

        # -------- ГРАФИК 1: Динамика (Линейный) --------
        fig1 = Figure(figsize=(7, 4))
        fig1.subplots_adjust(bottom=0.20)
        canvas1 = FigureCanvas(fig1)
        ax1 = fig1.add_subplot(111)
        ax1.plot(t, S, 'b-', label='Восприимчивые (S)')
        ax1.plot(t, E, 'y--', label='Латентные (E)')
        ax1.plot(t, I, 'r-', label='Инфицированные (I)', linewidth=2)
        ax1.plot(t, R, 'g-', label='Выздоровевшие (R)')
        ax1.set_title("Развитие эпидемии");
        ax1.set_xlabel("Время")
        ax1.legend();
        ax1.grid(True, alpha=0.3)
        self.time_tab.layout().addWidget(NavigationToolbar(canvas1, self))
        self.time_tab.layout().addWidget(canvas1)

        # -------- ГРАФИК 2: Распределение (Проценты) --------
        fig2 = Figure(figsize=(7, 4))
        fig2.subplots_adjust(bottom=0.20)
        canvas2 = FigureCanvas(fig2)
        ax2 = fig2.add_subplot(111)
        # Просто заполняем области, чтобы было понятнее, чем Stackplot
        # 1. Слой Инфицированных (от 0 до I)
        ax2.fill_between(t, 0, I, color='red', alpha=0.5, label='Болеют (I)')

        # 2. Слой Латентных (от I до I + E)
        ax2.fill_between(t, I, I + E, color='orange', alpha=0.4, label='Инкубация (E)')

        # 3. Слой Здоровых (от I + E до I + E + S)
        ax2.fill_between(t, I + E, I + E + S, color='blue', alpha=0.2, label='Здоровые (S)')

        # 4. Слой Выздоровевших (от I + E + S до 1.0)
        # Все, кто выше границы здоровых — это выздоровевшие
        ax2.plot(t, I + E + S, 'b-', alpha=0.2)  # Верхняя граница восприимчивых
        ax2.set_title("Нагрузка на систему здравоохранения")
        ax2.set_ylabel("Доля населения")
        ax2.set_xlabel("Время")
        ax2.legend()
        ax2.grid(True, alpha=0.2)
        self.area_tab.layout().addWidget(NavigationToolbar(canvas2, self))
        self.area_tab.layout().addWidget(canvas2)

        # -------- ГРАФИК 3: Фазовый портрет (С ТОЧКАМИ) --------
        fig3 = Figure(figsize=(7, 4))
        fig3.subplots_adjust(bottom=0.20)
        canvas3 = FigureCanvas(fig3)
        ax3 = fig3.add_subplot(111)
        ax3.plot(E, I, color="purple", linewidth=2, label="Траектория")
        # Возвращаем точки
        ax3.scatter([E[0]], [I[0]], color="green", s=50, label="Старт", zorder=5)
        ax3.scatter([E[-1]], [I[-1]], color="red", s=50, label="Конец", zorder=5)
        ax3.set_xlabel("E (Латентные)");
        ax3.set_ylabel("I (Инфицированные)")
        ax3.set_title("Фазовый портрет: Связь E и I");
        ax3.legend();
        ax3.grid(True)
        self.phase_tab.layout().addWidget(NavigationToolbar(canvas3, self))
        self.phase_tab.layout().addWidget(canvas3)

        # -------- ГРАФИК 4: Коэффициент воспроизводства (Rt) --------
        fig_rt = Figure(figsize=(7, 4))
        fig_rt.subplots_adjust(bottom=0.20)
        canvas_rt = FigureCanvas(fig_rt)
        ax_rt = fig_rt.add_subplot(111)

        ax_rt.plot(t, Rt, color='purple', linewidth=2, label='Rt(t)')
        # Критическая линия 1.0
        ax_rt.axhline(1.0, color='red', linestyle='--', linewidth=1.5, label='Порог эпидемии (1.0)')

        # Закрасим область выше единицы (рост) и ниже (затухание)
        ax_rt.fill_between(t, 1.0, Rt, where=(Rt > 1.0), color='red', alpha=0.1)
        ax_rt.fill_between(t, 1.0, Rt, where=(Rt <= 1.0), color='green', alpha=0.1)

        ax_rt.set_title("Эффективное репродуктивное число ($R_t$)")
        ax_rt.set_xlabel("Время");
        ax_rt.set_ylabel("Rt")
        ax_rt.legend();
        ax_rt.grid(True, alpha=0.3)
        self.rt_tab.layout().addWidget(NavigationToolbar(canvas_rt, self))
        self.rt_tab.layout().addWidget(canvas_rt)

        # -------- ГРАФИК 5: Новые случаи в день (Incidence) --------
        fig_inc = Figure(figsize=(7, 4))
        fig_inc.subplots_adjust(bottom=0.20)
        canvas_inc = FigureCanvas(fig_inc)
        ax_inc = fig_inc.add_subplot(111)

        ax_inc.bar(t, incidence, width=(t[1] - t[0]) * 0.8, color='salmon', alpha=0.6, label='Прирост (E -> I)')
        ax_inc.plot(t, incidence, color='red', linewidth=1.5)  # Плавная линия поверх баров

        ax_inc.set_title("Скорость появления новых инфицированных")
        ax_inc.set_xlabel("Время");
        ax_inc.set_ylabel("Доля новых случаев")
        ax_inc.legend();
        ax_inc.grid(True, alpha=0.3)
        self.incidence_tab.layout().addWidget(NavigationToolbar(canvas_inc, self))
        self.incidence_tab.layout().addWidget(canvas_inc)

        # -------- ГРАФИК: Летальность (Смертность) --------
        fig_d = Figure(figsize=(7, 4))
        fig_d.subplots_adjust(bottom=0.20)
        canvas_d = FigureCanvas(fig_d)
        ax_d = fig_d.add_subplot(111)
        ax_d.stackplot(t, Recovered_Actual, Deaths, colors=['green', 'black'],
                       labels=['Выжившие', 'Умершие'], alpha=0.7)
        ax_d.set_title("Исход заболевания (Накопительно)")
        ax_d.set_ylabel("Доля населения")
        ax_d.set_xlabel("Время")
        ax_d.legend(loc='upper left')
        self.death_tab.layout().addWidget(NavigationToolbar(canvas_d, self))
        self.death_tab.layout().addWidget(canvas_d)

        # -------- ГРАФИК: Темп роста (%) --------
        fig_g = Figure(figsize=(7, 4))
        fig_g.subplots_adjust(bottom=0.20)
        canvas_g = FigureCanvas(fig_g)
        ax_g = fig_g.add_subplot(111)

        # Рисуем линию темпа роста
        ax_g.plot(t, growth_rate, color='brown', linewidth=2, label='Темп роста I')
        ax_g.axhline(0, color='black', linestyle='--', alpha=0.5)  # Линия стабильности

        # Закрашиваем области роста и спада
        ax_g.fill_between(t, 0, growth_rate, where=(growth_rate > 0), color='red', alpha=0.1)
        ax_g.fill_between(t, 0, growth_rate, where=(growth_rate <= 0), color='green', alpha=0.1)

        ax_g.set_title("Ежедневный темп изменения числа больных")
        ax_g.set_ylabel("Прирост (%)")
        ax_g.set_xlabel("Время")
        ax_g.set_ylim(-20, 50)  # Ограничим для наглядности (можно убрать)
        ax_g.grid(True, alpha=0.2)
        self.growth_tab.layout().addWidget(NavigationToolbar(canvas_g, self))
        self.growth_tab.layout().addWidget(canvas_g)

        # -------- ГРАФИК 6: Итоговая статистика (Вместо скоростей) --------
        fig4 = Figure(figsize=(7, 4));
        canvas4 = FigureCanvas(fig4)
        ax4 = fig4.add_subplot(111)
        ax4.axis('off')  # Убираем оси, это будет текстовая панель

        stats_text = (
            f"ОТЧЕТ ПО МОДЕЛИ SEIR\n"
            f"-------------------------------------\n"
            f"• Время достижения пика: {t_peak:.2f} ед.\n"
            f"• Максимальный процент зараженных: {i_max * 100:.2f}%\n"
            f"• Итоговый процент переболевших: {total_affected:.2f}%\n"
            f"• Оставшиеся здоровыми (S): {S[-1] * 100:.2f}%\n"
            f"-------------------------------------\n"
            f"Статус: Эпидемия купирована" if I[-1] < 0.001 else "Статус: Процесс продолжается"
        )
        ax4.text(0.5, 0.5, stats_text, transform=ax4.transAxes,
                 fontsize=12, va='center', ha='center',
                 bbox=dict(boxstyle="round,pad=1", facecolor='wheat', alpha=0.3))

        self.stats_tab.layout().addWidget(canvas4)

    # ================= СОХРАНЕНИЕ И ЗАГРУЗКА =================

    def save_current_calculation(self):
        if not self.t_data:
            QMessageBox.warning(self, "Предупреждение", "Нет данных для сохранения!")
            return False

        if not self.current_calc_id:
            self.current_calc_id = str(uuid.uuid4())

        calc_data = {
            'id': self.current_calc_id,
            'model_name': 'Модель эпидемии SEIR',  # Убедитесь, что это совпадает с ожиданием в main_window
            'beta': float(self.beta_input.text()),
            'alpha': float(self.alpha_input.text()),
            'gamma': float(self.gamma_input.text()),
            'S0': float(self.S0_input.text()),
            'E0': float(self.E0_input.text()),
            'I0': float(self.I0_input.text()),
            'R0': float(self.R0_input.text()),
            't_max': float(self.t_max_input.text()),
            'timestamp': datetime.now().isoformat(),
            't_data': [float(v) for v in self.t_data],
            'S_data': [float(v) for v in self.S_data],
            'E_data': [float(v) for v in self.E_data],
            'I_data': [float(v) for v in self.I_data],
            'R_data': [float(v) for v in self.R_data]
        }

        result = save_calculation(calc_data)
        QMessageBox.information(self, "Сохранение", result)
        return True

    def load_calculation_by_id(self, calc_id):
        calc = load_calculation(calc_id)
        if calc:
            self.current_calc_id = calc_id

            self.beta_input.setText(str(calc.get('beta', '0.5')))
            self.alpha_input.setText(str(calc.get('alpha', '0.2')))
            self.gamma_input.setText(str(calc.get('gamma', '0.1')))

            self.t_max_input.setText(str(calc.get('t_max', '150')))

            self.S0_input.setText(str(calc.get('S0', '0.98')))
            self.E0_input.setText(str(calc.get('E0', '0.01')))
            self.I0_input.setText(str(calc.get('I0', '0.01')))
            self.R0_input.setText(str(calc.get('R0', '0.0')))

            if 't_data' in calc:
                self.t_data = calc['t_data']
                self.S_data = calc['S_data']
                self.E_data = calc['E_data']
                self.I_data = calc['I_data']
                self.R_data = calc['R_data']
                self.plot_graphs()
            return True
        return False