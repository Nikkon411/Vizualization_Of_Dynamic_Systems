from datetime import datetime
import uuid
import numpy as np

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QSpacerItem,
    QSizePolicy, QTabWidget, QProgressBar, QMessageBox, QSlider
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from core.calculation_thread import CalculationThread
from core.database import save_calculation, load_calculation


class LotkaVolterraTab(QWidget):
    """Вкладка: Модель Лотки–Вольтерра"""

    def __init__(self):
        super().__init__()
        # Инициализация переменных ДО интерфейса
        self.t_data = []
        self.x_data = []
        self.y_data = []
        self.calculation_thread = None
        self.current_calc_id = None
        self.is_animating = False
        self.current_frame = 0
        self.anim_timer = None
        self.canvas_anim = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("Система Лотки–Вольтерра (Хищник-Жертва)")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form_layout = QFormLayout()
        self.alpha_input = QLineEdit("0.1")
        self.beta_input = QLineEdit("0.02")
        self.gamma_input = QLineEdit("0.3")
        self.delta_input = QLineEdit("0.01")
        self.x0_input = QLineEdit("10")
        self.y0_input = QLineEdit("5")

        form_layout.addRow("α (рост жертв):", self.alpha_input)
        form_layout.addRow("β (смертность жертв):", self.beta_input)
        form_layout.addRow("γ (смертность хищников):", self.gamma_input)
        form_layout.addRow("δ (рост хищников):", self.delta_input)
        form_layout.addRow("x₀ (нач. популяция жертв):", self.x0_input)
        form_layout.addRow("y₀ (нач. популяция хищников):", self.y0_input)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)

        self.calc_button = QPushButton("Рассчитать")
        self.calc_button.clicked.connect(self.on_calculate)

        self.graph_tabs = QTabWidget()
        self.time_tab = QWidget()
        self.phase_tab = QWidget()
        self.vector_tab = QWidget()
        self.animation_tab = QWidget()

        for tab in [self.time_tab, self.phase_tab, self.vector_tab, self.animation_tab]:
            tab.setLayout(QVBoxLayout())

        self.graph_tabs.addTab(self.time_tab, "Динамика во времени")
        self.graph_tabs.addTab(self.phase_tab, "Фазовый портрет")
        self.graph_tabs.addTab(self.vector_tab, "Векторное поле")
        self.graph_tabs.addTab(self.animation_tab, "Анимация")

        layout.addWidget(title)
        layout.addLayout(form_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.calc_button)
        layout.addWidget(self.graph_tabs)

        self.setLayout(layout)

    def on_calculate(self):
        if self.calculation_thread and self.calculation_thread.isRunning():
            return
        try:
            params = [self.alpha_input.text(), self.beta_input.text(), self.gamma_input.text(),
                      self.delta_input.text(), self.x0_input.text(), self.y0_input.text()]
            if not all(params):
                QMessageBox.warning(self, "Предупреждение", "Заполните все поля!")
                return
            self.calc_button.setEnabled(False)
            self.calc_button.setText("⏳ Вычисление...")
            self.progress_bar.setVisible(True)
            self.calculation_thread = CalculationThread(*params, model="lotka")
            self.calculation_thread.calculation_finished.connect(self.on_finished)
            self.calculation_thread.calculation_error.connect(self.on_error)
            self.calculation_thread.start()
        except Exception as e:
            self.on_error(str(e))

    def on_error(self, error):
        self.calc_button.setEnabled(True)
        self.calc_button.setText("Рассчитать")
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Ошибка", f"Ошибка расчета: {error}")

    def on_finished(self, result):
        self.calc_button.setEnabled(True)
        self.calc_button.setText("Рассчитать")
        self.progress_bar.setVisible(False)
        self.t_data = [float(row[0]) for row in result]
        self.x_data = [float(row[1]) for row in result]
        self.y_data = [float(row[2]) for row in result]
        self.plot_graphs(self.t_data, self.x_data, self.y_data)
        self.create_animation(self.t_data, self.x_data, self.y_data)

    def plot_graphs(self, t, x, y):
        for tab in [self.time_tab, self.phase_tab, self.vector_tab]:
            layout = tab.layout()
            while layout.count():
                item = layout.takeAt(0)
                if item.widget(): item.widget().deleteLater()

        fig_time = Figure(figsize=(7, 4))
        fig_time.subplots_adjust(bottom=0.20)
        canvas_time = FigureCanvas(fig_time)
        ax1 = fig_time.add_subplot(111)
        ax1.plot(t, x, label="Жертвы", color='blue')
        ax1.plot(t, y, label="Хищники", color='red')
        ax1.set_xlabel("t");
        ax1.set_ylabel("Популяция");
        ax1.legend();
        ax1.grid(True)
        self.time_tab.layout().addWidget(NavigationToolbar(canvas_time, self))
        self.time_tab.layout().addWidget(canvas_time)

        fig_phase = Figure(figsize=(7, 4))
        fig_phase.subplots_adjust(bottom=0.20)
        canvas_phase = FigureCanvas(fig_phase)
        ax2 = fig_phase.add_subplot(111)
        ax2.plot(x, y, color='green')
        ax2.set_xlabel("Жертвы");
        ax2.set_ylabel("Хищники");
        ax2.set_title("Фазовый портрет");
        ax2.grid(True)
        self.phase_tab.layout().addWidget(NavigationToolbar(canvas_phase, self))
        self.phase_tab.layout().addWidget(canvas_phase)

        fig_vec = Figure(figsize=(7, 4))
        fig_vec.subplots_adjust(bottom=0.20)
        canvas_vec = FigureCanvas(fig_vec)
        ax3 = fig_vec.add_subplot(111)
        X, Y = np.meshgrid(np.linspace(min(x) * 0.8, max(x) * 1.2, 20), np.linspace(min(y) * 0.8, max(y) * 1.2, 20))
        U = float(self.alpha_input.text()) * X - float(self.beta_input.text()) * X * Y
        V = float(self.delta_input.text()) * X * Y - float(self.gamma_input.text()) * Y
        ax3.quiver(X, Y, U, V, color='red', alpha=0.5)
        ax3.plot(x, y, color='green')
        ax3.set_xlabel("Жертвы");
        ax3.set_ylabel("Хищники")
        self.vector_tab.layout().addWidget(NavigationToolbar(canvas_vec, self))
        self.vector_tab.layout().addWidget(canvas_vec)

    def create_animation(self, t, x, y):
        # 1. Остановка таймера и сброс состояния
        if hasattr(self, 'anim_timer') and self.anim_timer:
            self.anim_timer.stop()

        self.is_animating = False
        self.current_frame = 0

        # 2. Полная очистка layout
        layout = self.animation_tab.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    self._clear_layout(item.layout())

        # 3. Создание фигуры и холста
        fig_anim = Figure(figsize=(7, 5))
        fig_anim.subplots_adjust(left=0.15, bottom=0.22)
        self.canvas_anim = FigureCanvas(fig_anim)
        self.ax_anim = fig_anim.add_subplot(111)

        self.ax_anim.set_xlim(min(x) * 0.9, max(x) * 1.1)
        self.ax_anim.set_ylim(min(y) * 0.9, max(y) * 1.1)
        self.ax_anim.grid(True, alpha=0.3)
        self.ax_anim.set_xlabel("Жертвы")
        self.ax_anim.set_ylabel("Хищники")

        self.anim_line, = self.ax_anim.plot([], [], 'b-', linewidth=2)
        self.anim_point, = self.ax_anim.plot([], [], 'ro')
        self.anim_text = self.ax_anim.text(0.02, 0.95, '', transform=self.ax_anim.transAxes)

        # 4. Проверка таймера
        if self.anim_timer is None:
            self.anim_timer = QTimer(self)
            self.anim_timer.timeout.connect(self.advance_animation)

        # 5. Создание управления (Исправлено)
        ctrl = QHBoxLayout()

        # Наша новая кнопка-переключатель
        self.btn_toggle = QPushButton("▶ Пуск")
        self.btn_toggle.setFixedWidth(100)
        self.btn_toggle.clicked.connect(self.toggle_animation)

        btn_reset = QPushButton("⏹ Сброс")
        btn_reset.clicked.connect(self.reset_anim)

        # Слайдер (Влево - быстро, Вправо - медленно)
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(10, 200)
        self.speed_slider.setValue(100)  # Среднее значение
        self.speed_slider.setFixedWidth(150)
        self.speed_slider.valueChanged.connect(self.update_timer_interval)

        # Добавляем только существующие виджеты
        ctrl.addWidget(self.btn_toggle)
        ctrl.addWidget(btn_reset)
        ctrl.addStretch()
        ctrl.addWidget(QLabel("Скорость:"))
        ctrl.addWidget(self.speed_slider)

        layout.addWidget(self.canvas_anim)
        layout.addLayout(ctrl)

        self.update_anim_view()

    def toggle_animation(self):
        """Логика переключения кнопки Пуск/Пауза"""
        if not self.t_data:
            return

        if not self.is_animating:
            self.is_animating = True
            self.btn_toggle.setText("⏸ Пауза")
            # Считаем интервал с учетом инверсии (чтобы влево было быстрее)
            val = self.speed_slider.value()
            self.anim_timer.start(210 - val)
        else:
            self.is_animating = False
            self.btn_toggle.setText("▶ Пуск")
            self.anim_timer.stop()


    def _clear_layout(self, layout):
        """Вспомогательный метод для глубокой очистки слоев"""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    self._clear_layout(item.layout())

    def update_anim_view(self):
        """Безопасное обновление кадра анимации"""
        if not self.t_data or not hasattr(self, 'anim_line'):
            return
        idx = self.current_frame
        try:
            self.anim_line.set_data(self.x_data[:idx + 1], self.y_data[:idx + 1])
            self.anim_point.set_data([self.x_data[idx]], [self.y_data[idx]])
            self.anim_text.set_text(f'Время: {self.t_data[idx]:.1f}')
            self.canvas_anim.draw_idle()
        except Exception as e:
            print(f"Ошибка отрисовки: {e}")

    def update_timer_interval(self):
        """Обновление скорости 'на лету'"""
        if self.anim_timer:
            val = self.speed_slider.value()
            # Инвертируем: вправо (больше val) -> больше задержка -> медленнее
            # Влево (меньше val) -> меньше задержка -> быстрее
            self.anim_timer.setInterval(210 - val)

    def advance_animation(self):
        if self.t_data:
            self.current_frame += 1
            if self.current_frame >= len(self.t_data):
                self.current_frame = 0
            self.update_anim_view()

    def play_anim(self):
        if not self.t_data: return
        self.is_animating = True
        # Запускаем таймер с текущим значением слайдера
        self.anim_timer.start(self.speed_slider.value())

    def pause_anim(self):
        self.is_animating = False
        if self.anim_timer: self.anim_timer.stop()

    def reset_anim(self):
        """Полный сброс"""
        self.is_animating = False
        if self.anim_timer:
            self.anim_timer.stop()

        # Сбрасываем текст кнопки
        if hasattr(self, 'btn_toggle'):
            self.btn_toggle.setText("▶ Пуск")

        self.current_frame = 0
        self.update_anim_view()

    def save_current_calculation(self):
        if not self.t_data: return False
        if not self.current_calc_id: self.current_calc_id = str(uuid.uuid4())
        data = {
            'id': self.current_calc_id, 'model_name': 'Лотка-Вольтерра',
            'alpha': float(self.alpha_input.text()), 'beta': float(self.beta_input.text()),
            'gamma': float(self.gamma_input.text()), 'delta': float(self.delta_input.text()),
            'x0': float(self.x0_input.text()), 'y0': float(self.y0_input.text()),
            'timestamp': datetime.now().isoformat(),
            't_data': self.t_data, 'x_data': self.x_data, 'y_data': self.y_data
        }
        QMessageBox.information(self, "Сохранение", save_calculation(data))
        return True

    def load_calculation_by_id(self, calc_id):
        calc = load_calculation(calc_id)
        if calc:
            self.current_calc_id = calc_id
            self.alpha_input.setText(str(calc.get('alpha', '0.1')))
            self.beta_input.setText(str(calc.get('beta', '0.02')))
            self.gamma_input.setText(str(calc.get('gamma', '0.3')))
            self.delta_input.setText(str(calc.get('delta', '0.01')))
            self.x0_input.setText(str(calc.get('x0', '10')))
            self.y0_input.setText(str(calc.get('y0', '5')))
            self.t_data, self.x_data, self.y_data = calc['t_data'], calc['x_data'], calc['y_data']
            self.plot_graphs(self.t_data, self.x_data, self.y_data)
            self.create_animation(self.t_data, self.x_data, self.y_data)
            return True
        return False