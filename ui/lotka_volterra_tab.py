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
        self.current_calc_id = None
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

            # Проверяем, что все поля заполнены
            if not all([a, b, g, d, x0, y0]):
                QMessageBox.warning(self, "Предупреждение", "Заполните все поля!")
                return

            # Проверяем, что все значения являются числами
            def is_valid_number(value):
                try:
                    float(value)
                    return True
                except ValueError:
                    return False

            # Список полей для проверки с человеко-читаемыми названиями
            fields_to_check = [
                (a, "α (рост жертв)"),
                (b, "β (смертность жертв)"),
                (g, "γ (смертность хищников)"),
                (d, "δ (рост хищников)"),
                (x0, "x₀ (начальная популяция жертв)"),
                (y0, "y₀ (начальная популяция хищников)")
            ]

            # Проверяем каждое поле
            invalid_fields = []
            for value, field_name in fields_to_check:
                if not is_valid_number(value):
                    invalid_fields.append(field_name)

            # Если есть невалидные поля, показываем ошибку
            if invalid_fields:
                error_message = "Следующие поля содержат некорректные числовые значения:\n\n"
                for field in invalid_fields:
                    error_message += f"• {field}\n"
                error_message += "\nПожалуйста, введите корректные числа."

                QMessageBox.critical(self, "Ошибка ввода", error_message)
                return

            # Проверяем, что начальные популяции не отрицательные
            if float(x0) < 0 or float(y0) < 0:
                QMessageBox.warning(
                    self,
                    "Предупреждение",
                    "Начальные популяции не могут быть отрицательными!\n"
                    f"x₀ = {x0}, y₀ = {y0}"
                )
                return

            # Проверяем, что параметры не слишком большие (опционально)
            # Это предотвращает возможные проблемы с вычислениями
            for value, field_name in fields_to_check[:4]:  # Только α, β, γ, δ
                num_value = float(value)
                if abs(num_value) > 1000:  # Ограничение на очень большие значения
                    reply = QMessageBox.question(
                        self,
                        "Предупреждение",
                        f"Значение параметра {field_name} = {value} очень большое.\n"
                        "Это может привести к проблемам с вычислениями.\n"
                        "Продолжить расчет?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
                        return

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
            self.calc_button.setEnabled(True)
            self.calc_button.setText("🔢 Рассчитать")
            self.progress_bar.setVisible(False)
            self.show_error(f"Ошибка ввода: {e}")

    def on_calculation_finished(self, result):
        """Обработчик завершения вычислений"""
        # Восстанавливаем интерфейс
        self.calc_button.setEnabled(True)
        self.calc_button.setText("🔢 Рассчитать")
        self.progress_bar.setVisible(False)

        # Обрабатываем результат
        try:
            # Проверяем результат
            if result is None:
                self.show_error("Wolfram вернул пустой результат")
                return

            if not isinstance(result, list) or len(result) == 0:
                self.show_error("Некорректный результат от Wolfram")
                return

            # result — это список списков вида:
            # [[t0, x0, y0], [t1, x1, y1], ...]
            # Конвертируем numpy массивы в обычные списки Python
            self.t_data = [float(row[0]) for row in result]
            self.x_data = [float(row[1]) for row in result]
            self.y_data = [float(row[2]) for row in result]

            # Рисуем графики
            self.plot_graphs(self.t_data, self.x_data, self.y_data)
            # Создаем анимацию
            self.create_animation(self.t_data, self.x_data, self.y_data)

            # Сбрасываем текущий ID расчета (новый расчет)
            self.current_calc_id = None

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

        # Сбрасываем значения по умолчанию
        self.alpha_input.setText("0.1")
        self.beta_input.setText("0.02")
        self.gamma_input.setText("0.3")
        self.delta_input.setText("0.01")
        self.x0_input.setText("10")
        self.y0_input.setText("5")

        # Останавливаем анимацию если она есть
        self.stop_animation()

        # Восстанавливаем кнопки
        self.calc_button.setEnabled(True)
        self.calc_button.setText("🔢 Рассчитать")
        self.progress_bar.setVisible(False)

        # Сбрасываем текущий расчет
        self.current_calc_id = None

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
        """Запускает анимации"""
        if not self.t_data or self.is_animating:
            return

        self.is_animating = True

        # БЛОКИРУЕМ поле ввода скорости
        self.speed_slider.setEnabled(False)
        self.speed_slider.setStyleSheet("""
            QLineEdit {
                background-color: #3A3A4A;
                color: #888888;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
            }
        """)

        # Проверяем, что скорость - валидное число
        try:
            speed = int(self.speed_slider.text())
            if speed <= 0:
                speed = 50
                self.speed_slider.setText("50")
        except ValueError:
            speed = 50
            self.speed_slider.setText("50")

        self.animation_timer = self.startTimer(speed)

    def pause_animation(self):
        """Останавливает анимацию"""
        self.is_animating = False

        # РАЗБЛОКИРУЕМ поле ввода скорости
        self.speed_slider.setEnabled(True)
        self.speed_slider.setStyleSheet("""
            QLineEdit {
                background-color: #2B2B3D;
                color: white;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 4px;
            }
        """)

        if hasattr(self, 'animation_timer'):
            try:
                self.killTimer(self.animation_timer)
            except:
                pass  # Игнорируем ошибки при уничтожении таймера

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

    def save_current_calculation(self):
        """Сохраняет текущий расчет в базу данных"""
        if not self.t_data:
            QMessageBox.warning(self, "Предупреждение", "Нет данных для сохранения! Сначала выполните расчет.")
            return False

        # Создаем уникальный ID если это новый расчет
        if not self.current_calc_id:
            self.current_calc_id = str(uuid.uuid4())

        # Подготавливаем данные для сохранения
        calc_data = {
            'id': self.current_calc_id,
            'model_name': 'Лотка-Вольтерра',
            'alpha': float(self.alpha_input.text()) if self.alpha_input.text() else 0.0,
            'beta': float(self.beta_input.text()) if self.beta_input.text() else 0.0,
            'gamma': float(self.gamma_input.text()) if self.gamma_input.text() else 0.0,
            'delta': float(self.delta_input.text()) if self.delta_input.text() else 0.0,
            'x0': float(self.x0_input.text()) if self.x0_input.text() else 0.0,
            'y0': float(self.y0_input.text()) if self.y0_input.text() else 0.0,
            'timestamp': datetime.now().isoformat(),
            't_data': [float(t) for t in self.t_data],
            'x_data': [float(x) for x in self.x_data],
            'y_data': [float(y) for y in self.y_data]
        }

        # Проверяем, существует ли уже такой расчет
        result = save_calculation(calc_data)

        try:
            QMessageBox.information(self, "Сохранение", result)
            return True

        except Exception as e:
            QMessageBox.warning(self, "Ошибка сохранения", f"Не удалось сохранить расчет: {str(e)}")
            return False

    def load_calculation_by_id(self, calc_id):
        """Загружает расчет по ID"""


        result = load_calculation(calc_id)

        if result:
            calc = result
            self.current_calc_id = calc_id

            # Заполняем поля формы
            self.alpha_input.setText(str(calc.get('alpha', '0.1')))
            self.beta_input.setText(str(calc.get('beta', '0.02')))
            self.gamma_input.setText(str(calc.get('gamma', '0.3')))
            self.delta_input.setText(str(calc.get('delta', '0.01')))
            self.x0_input.setText(str(calc.get('x0', '10')))
            self.y0_input.setText(str(calc.get('y0', '5')))

            # Если есть данные для графиков, отображаем их
            if 't_data' in calc and 'x_data' in calc and 'y_data' in calc:
                self.t_data = [float(t) for t in calc['t_data']]
                self.x_data = [float(x) for x in calc['x_data']]
                self.y_data = [float(y) for y in calc['y_data']]

                if self.t_data and self.x_data and self.y_data:
                    self.plot_graphs(self.t_data, self.x_data, self.y_data)
                    self.create_animation(self.t_data, self.x_data, self.y_data)

            return True
        return False