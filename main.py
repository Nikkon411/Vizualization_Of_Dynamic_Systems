from wolfram_connector import WolframConnector
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
import numpy as np
import threading
from PyQt6.QtCore import QThread, pyqtSignal

# путь к ядру
WOLFRAM_PATH = r"C:\Program Files\Wolfram Research\Wolfram\14.3\WolframKernel.exe"

wolfram = WolframConnector(kernel_path=WOLFRAM_PATH)
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QSpacerItem, QSizePolicy,
    QTabWidget, QProgressBar
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt


class CalculationThread(QThread):
    """Поток для вычислений в Wolfram"""
    calculation_finished = pyqtSignal(list)  # Сигнал с результатом
    calculation_error = pyqtSignal(str)  # Сигнал с ошибкой
    calculation_started = pyqtSignal()  # Сигнал начала вычислений

    def __init__(self, alpha, beta, gamma, delta, x0, y0):
        super().__init__()
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.delta = delta
        self.x0 = x0
        self.y0 = y0

    def run(self):
        try:
            self.calculation_started.emit()

            # Wolfram запрос: вычисляем численное решение и таблицу
            expr = f"""
            sol = NDSolve[{{
                x'[t] == {self.alpha}*x[t] - {self.beta}*x[t]*y[t],
                y'[t] == {self.delta}*x[t]*y[t] - {self.gamma}*y[t],
                x[0] == {self.x0},
                y[0] == {self.y0}
            }}, {{x, y}}, {{t, 0, 50}}];

            Table[{{
                t,
                Evaluate[x[t] /. sol[[1]]],
                Evaluate[y[t] /. sol[[1]]]
            }}, {{t, 0, 50, 0.1}}]
            """

            result = wolfram.evaluate(expr)
            self.calculation_finished.emit(result)

        except Exception as e:
            self.calculation_error.emit(str(e))


class LotkaVolterraTab(QWidget):
    """Вкладка: Модель Лотки–Вольтерра"""

    def __init__(self):
        super().__init__()
        self.animation = None
        self.current_frame = 0
        self.is_animating = False
        self.t_data = []
        self.x_data = []
        self.y_data = []
        self.calculation_thread = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Заголовок
        title = QLabel("Симуляция системы Лотки–Вольтерра")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Введите параметры модели и запустите расчёт")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #AAAAAA; font-size: 13px;")

        # Форма ввода параметров
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

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

        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Бесконечный прогресс-бар

        # Кнопки расчёта и очистки
        self.calc_button = QPushButton("🔢 Рассчитать")
        self.calc_button.clicked.connect(self.on_calculate)

        self.clear_button = QPushButton("🧹 Очистить")
        self.clear_button.clicked.connect(self.on_clear)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(self.calc_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch(1)

        # Вкладки графиков
        self.graph_tabs = QTabWidget()
        self.graph_tabs.currentChanged.connect(self.on_tab_changed)
        self.graph_tabs.setStyleSheet("""
            QTabBar::tab {
                background: #2E2E3F;
                color: #CCC;
                padding: 6px 12px;
            }
            QTabBar::tab:selected {
                background: #3C8DAD;
                color: white;
            }
        """)

        # Создаем вкладки под графики
        self.time_tab = QWidget()
        self.phase_tab = QWidget()
        self.vector_tab = QWidget()
        self.animation_tab = QWidget()

        for tab in [self.time_tab, self.phase_tab, self.vector_tab, self.animation_tab]:
            tab.setLayout(QVBoxLayout())

        self.graph_tabs.addTab(self.time_tab, "Популяции по времени")
        self.graph_tabs.addTab(self.phase_tab, "Фазовый портрет")
        self.graph_tabs.addTab(self.vector_tab, "Векторное поле")
        self.graph_tabs.addTab(self.animation_tab, "Анимация фазового портрета")

        # Добавляем всё в основной layout
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
        layout.addItem(QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.setLayout(layout)

    def on_calculate(self):
        # Если уже идет вычисление, не запускаем новое
        if self.calculation_thread and self.calculation_thread.isRunning():
            return

        try:
            # Получаем параметры
            a = self.alpha_input.text()
            b = self.beta_input.text()
            g = self.gamma_input.text()
            d = self.delta_input.text()
            x0 = self.x0_input.text()
            y0 = self.y0_input.text()

            # Блокируем кнопку расчета
            self.calc_button.setEnabled(False)
            self.calc_button.setText("⏳ Вычисление...")
            self.progress_bar.setVisible(True)

            # Создаем и запускаем поток вычислений
            self.calculation_thread = CalculationThread(a, b, g, d, x0, y0)
            self.calculation_thread.calculation_finished.connect(self.on_calculation_finished)
            self.calculation_thread.calculation_error.connect(self.on_calculation_error)
            self.calculation_thread.start()

        except Exception as e:
            self.show_error(f"Ошибка ввода: {e}")

    def on_calculation_finished(self, result):
        """Обработчик завершения вычислений"""
        # Восстанавливаем интерфейс
        self.calc_button.setEnabled(True)
        self.calc_button.setText("🔢 Рассчитать")
        self.progress_bar.setVisible(False)

        # Обрабатываем результат
        try:
            # result — это список списков вида:
            # [[t0, x0, y0], [t1, x1, y1], ...]
            self.t_data = [row[0] for row in result]
            self.x_data = [row[1] for row in result]
            self.y_data = [row[2] for row in result]

            # Рисуем графики
            self.plot_graphs(self.t_data, self.x_data, self.y_data)
            # Создаем анимацию
            self.create_animation(self.t_data, self.x_data, self.y_data)

        except Exception as e:
            self.show_error(f"Ошибка обработки результатов: {e}")

    def on_calculation_error(self, error_message):
        """Обработчик ошибки вычислений"""
        # Восстанавливаем интерфейс
        self.calc_button.setEnabled(True)
        self.calc_button.setText("🔢 Рассчитать")
        self.progress_bar.setVisible(False)

        self.show_error(f"Ошибка Wolfram: {error_message}")

    def show_error(self, message):
        """Показывает сообщение об ошибке"""
        error_label = QLabel(message)
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setStyleSheet("color: red; background-color: #2B2B3D; padding: 10px; border-radius: 5px;")

        # Показываем ошибку на всех вкладках
        for tab in [self.time_tab, self.phase_tab, self.vector_tab, self.animation_tab]:
            layout = tab.layout()
            for i in reversed(range(layout.count())):
                widget = layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            layout.addWidget(QLabel(message))

    def on_tab_changed(self, index):
        """Обработчик переключения вкладок"""
        tab_name = self.graph_tabs.tabText(index)
        if tab_name != "Анимация фазового портрета" and self.is_animating:
            self.pause_animation()
        elif tab_name == "Анимация фазового портрета" and not self.is_animating and hasattr(self, 'canvas_anim'):
            # При переключении на вкладку анимации обновляем отображение
            self.update_animation_display()

    def on_clear(self):
        # Останавливаем вычисления если они идут
        if self.calculation_thread and self.calculation_thread.isRunning():
            self.calculation_thread.terminate()
            self.calculation_thread.wait()

        for box in [self.alpha_input, self.beta_input, self.gamma_input,
                    self.delta_input, self.x0_input, self.y0_input]:
            box.clear()

        # Останавливаем анимацию если она есть
        self.stop_animation()

        # Восстанавливаем кнопку
        self.calc_button.setEnabled(True)
        self.calc_button.setText("🔢 Рассчитать")
        self.progress_bar.setVisible(False)

        # Очищаем данные
        self.t_data = []
        self.x_data = []
        self.y_data = []
        self.current_frame = 0

        # Очищаем все вкладки
        for tab in [self.time_tab, self.phase_tab, self.vector_tab, self.animation_tab]:
            layout = tab.layout()
            for i in reversed(range(layout.count())):
                widget = layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()

            placeholder = QLabel("График появится здесь после расчёта")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: #888888; font-style: italic;")
            layout.addWidget(placeholder)

    def plot_graphs(self, t, x, y):
        # Удаляем старое содержимое всех вкладок
        for tab in [self.time_tab, self.phase_tab, self.vector_tab]:
            layout = tab.layout()
            for i in reversed(range(layout.count())):
                widget = layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()

        # ---------- 1. Популяции по времени ----------
        fig_time = Figure(figsize=(7, 4), dpi=100)
        fig_time.subplots_adjust(bottom=0.15)
        canvas_time = FigureCanvas(fig_time)
        ax_time = fig_time.add_subplot(111)
        ax_time.plot(t, x, label="Жертвы", color='blue')
        ax_time.plot(t, y, label="Хищники", color='red')
        ax_time.set_xlabel("Время t")
        ax_time.set_ylabel("Популяция")
        ax_time.set_title("Динамика популяций")
        ax_time.grid(True)
        ax_time.legend()
        self.time_tab.layout().addWidget(canvas_time)

        # ---------- 2. Фазовый портрет ----------
        fig_phase = Figure(figsize=(7, 4), dpi=100)
        fig_phase.subplots_adjust(bottom=0.15)
        canvas_phase = FigureCanvas(fig_phase)
        ax_phase = fig_phase.add_subplot(111)
        ax_phase.plot(x, y, label="Фазовая траектория", color='green')
        ax_phase.set_xlabel("Жертвы (x)")
        ax_phase.set_ylabel("Хищники (y)")
        ax_phase.set_title("Фазовый портрет")
        ax_phase.grid(True)
        ax_phase.legend()
        self.phase_tab.layout().addWidget(canvas_phase)

        # ---------- 3. Векторное поле ----------
        fig_vector = Figure(figsize=(7, 4), dpi=100)
        fig_vector.subplots_adjust(bottom=0.15)
        canvas_vector = FigureCanvas(fig_vector)
        ax_vector = fig_vector.add_subplot(111)

        # Создаем сетку
        X, Y = np.meshgrid(np.linspace(min(x) * 0.8, max(x) * 1.2, 20),
                           np.linspace(min(y) * 0.8, max(y) * 1.2, 20))
        U = float(self.alpha_input.text()) * X - float(self.beta_input.text()) * X * Y
        V = float(self.delta_input.text()) * X * Y - float(self.gamma_input.text()) * Y
        ax_vector.quiver(X, Y, U, V, color='r', alpha=0.6)
        ax_vector.plot(x, y, 'g-', alpha=0.7, label="Траектория")
        ax_vector.set_xlabel("Жертвы (x)")
        ax_vector.set_ylabel("Хищники (y)")
        ax_vector.set_title("Векторное поле с траекторией")
        ax_vector.grid(True)
        ax_vector.legend()
        self.vector_tab.layout().addWidget(canvas_vector)

    def create_animation(self, t, x, y):
        """Создает анимацию фазового портрета"""
        # Очищаем вкладку анимации
        layout = self.animation_tab.layout()
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Создаем фигуру и canvas для анимации с уменьшенным графиком
        fig_anim = Figure(figsize=(7, 5), dpi=100)
        # Увеличиваем отступы вокруг графика, чтобы все поместилось
        fig_anim.subplots_adjust(left=0.15, right=0.95, bottom=0.22, top=0.88)

        self.canvas_anim = FigureCanvas(fig_anim)
        self.ax_anim = fig_anim.add_subplot(111)

        # Настраиваем оси с небольшим запасом
        x_margin = (max(x) - min(x)) * 0.1
        y_margin = (max(y) - min(y)) * 0.1
        self.ax_anim.set_xlim(min(x) - x_margin, max(x) + x_margin)
        self.ax_anim.set_ylim(min(y) - y_margin, max(y) + y_margin)

        # Уменьшаем шрифт подписей
        self.ax_anim.set_xlabel("Жертвы (x)", fontsize=10, labelpad=8)
        self.ax_anim.set_ylabel("Хищники (y)", fontsize=10, labelpad=8)
        self.ax_anim.set_title("Анимация фазового портрета", fontsize=12, pad=10)
        self.ax_anim.grid(True, alpha=0.3)

        # Уменьшаем шрифт меток на осях
        self.ax_anim.tick_params(axis='both', which='major', labelsize=9)

        # Создаем элементы для анимации
        self.line, = self.ax_anim.plot([], [], 'b-', linewidth=2, label='Траектория')
        self.point, = self.ax_anim.plot([], [], 'ro', markersize=6, label='Текущее состояние')

        # Уменьшаем информационную панель и перемещаем ее
        self.time_text = self.ax_anim.text(0.02, 0.98, '', transform=self.ax_anim.transAxes,
                                           fontsize=9, verticalalignment='top',
                                           bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.9))

        # Уменьшаем легенду
        self.ax_anim.legend(loc='upper right', framealpha=0.9, fontsize=9)

        # Инициализируем отображение
        self.current_frame = 0
        self.update_animation_display()

        # Добавляем управление анимацией
        control_layout = QHBoxLayout()

        self.play_button = QPushButton("▶ Воспроизвести")
        self.pause_button = QPushButton("⏸ Пауза")
        self.reset_button = QPushButton("⏹ Сбросить")
        self.slider_label = QLabel("Скорость:")
        self.speed_slider = QLineEdit("50")
        self.speed_slider.setMaximumWidth(50)
        self.speed_slider.setToolTip("Интервал между кадрами (мс)")

        self.play_button.clicked.connect(self.play_animation)
        self.pause_button.clicked.connect(self.pause_animation)
        self.reset_button.clicked.connect(self.reset_animation)
        self.speed_slider.textChanged.connect(self.on_speed_changed)

        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.reset_button)
        control_layout.addStretch()
        control_layout.addWidget(self.slider_label)
        control_layout.addWidget(self.speed_slider)

        # Создаем контейнер для управления
        control_widget = QWidget()
        control_widget.setLayout(control_layout)

        # Добавляем на вкладку
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.canvas_anim)
        main_layout.addWidget(control_widget)

        # Очищаем текущий layout и устанавливаем новый
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().deleteLater()

        container = QWidget()
        container.setLayout(main_layout)
        layout.addWidget(container)

    def update_animation_display(self):
        """Обновляет отображение анимации без использования FuncAnimation"""
        if not self.t_data:
            return

        # Ограничиваем текущий кадр
        if self.current_frame >= len(self.t_data):
            self.current_frame = len(self.t_data) - 1

        # Обновляем график
        self.line.set_data(self.x_data[:self.current_frame + 1], self.y_data[:self.current_frame + 1])
        self.point.set_data([self.x_data[self.current_frame]], [self.y_data[self.current_frame]])
        self.time_text.set_text(
            f'Время: {self.t_data[self.current_frame]:.1f}\nЖертвы: {self.x_data[self.current_frame]:.1f}\nХищники: {self.y_data[self.current_frame]:.1f}')

        # Перерисовываем canvas
        self.canvas_anim.draw_idle()

    def play_animation(self):
        """Запускает анимацию"""
        if not self.t_data or self.is_animating:
            return

        self.is_animating = True
        self.animation_timer = self.startTimer(int(self.speed_slider.text()))

    def pause_animation(self):
        """Останавливает анимацию"""
        self.is_animating = False
        if hasattr(self, 'animation_timer'):
            self.killTimer(self.animation_timer)

    def stop_animation(self):
        """Полностью останавливает анимацию"""
        self.pause_animation()
        if hasattr(self, 'animation'):
            self.animation = None

    def reset_animation(self):
        """Сбрасывает анимацию в начало"""
        self.pause_animation()
        self.current_frame = 0
        self.update_animation_display()

    def on_speed_changed(self):
        """Изменяет скорость анимации"""
        if self.is_animating:
            self.pause_animation()
            self.play_animation()

    def timerEvent(self, event):
        """Обработчик таймера для анимации"""
        if self.is_animating:
            self.current_frame += 1
            if self.current_frame >= len(self.t_data):
                self.current_frame = 0  # Зацикливаем анимацию
            self.update_animation_display()


class PlaceholderTab(QWidget):
    """Пустая вкладка-заглушка для будущих моделей"""

    def __init__(self, title):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel(f"<b>{title}</b><br><br>Эта модель будет добавлена позже.")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #AAAAAA; font-size: 14px; font-style: italic;")
        layout.addWidget(label)
        self.setLayout(layout)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Симуляция динамических систем")
        self.resize(1200, 800)
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E2F;
                color: #FFFFFF;
                font-family: "Segoe UI";
            }
            QTabWidget::pane {
                border-top: 2px solid #444;
                background-color: #2B2B3D;
            }
            QTabBar::tab {
                background-color: #2E2E3F;
                color: #CCC;
                padding: 8px 18px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin: 2px;
            }
            QTabBar::tab:selected {
                background-color: #3C8DAD;
                color: white;
            }
            QPushButton {
                background-color: #3C8DAD;
                color: white;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #47A7C4;
            }
            QPushButton:disabled {
                background-color: #2E2E3F;
                color: #888888;
            }
            QLineEdit {
                background-color: #2B2B3D;
                color: white;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 4px;
            }
            QProgressBar {
                border: 1px solid #444;
                border-radius: 4px;
                background-color: #2B2B3D;
                color: white;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3C8DAD;
                border-radius: 2px;
            }
        """)

        tabs = QTabWidget()
        tabs.addTab(LotkaVolterraTab(), "Лотка–Вольтерра")
        tabs.addTab(PlaceholderTab("Маятник"), "Маятник")
        tabs.addTab(PlaceholderTab("Система Лоренца"), "Система Лоренца")
        tabs.addTab(PlaceholderTab("Химическая реакция"), "Химическая реакция")

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())