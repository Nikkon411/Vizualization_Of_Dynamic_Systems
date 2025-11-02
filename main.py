from wolfram_connector import WolframConnector

# путь к ядру
WOLFRAM_PATH = r"C:\Program Files\Wolfram Research\Wolfram\14.3\WolframKernel.exe"

wolfram = WolframConnector(kernel_path=WOLFRAM_PATH)
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QSpacerItem, QSizePolicy,
    QTabWidget
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt


class LotkaVolterraTab(QWidget):
    """Вкладка: Модель Лотки–Вольтерра"""
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("Симуляция системы Лотки–Вольтерра")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Введите параметры модели и запустите расчёт")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #AAAAAA; font-size: 13px;")

        # Форма
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

        # Кнопки
        self.calc_button = QPushButton("🔢 Рассчитать")
        self.calc_button.clicked.connect(self.on_calculate)

        self.clear_button = QPushButton("🧹 Очистить")
        self.clear_button.clicked.connect(self.on_clear)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(self.calc_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch(1)

        # Зона графика
        self.graph_frame = QFrame()
        self.graph_frame.setStyleSheet("""
            QFrame {
                background-color: #2B2B3D;
                border: 1px solid #555;
                border-radius: 10px;
            }
        """)
        self.graph_frame.setMinimumHeight(250)
        graph_label = QLabel("График появится здесь после расчёта")
        graph_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        graph_label.setStyleSheet("color: #888888; font-style: italic;")
        graph_layout = QVBoxLayout()
        graph_layout.addWidget(graph_label)
        self.graph_frame.setLayout(graph_layout)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        layout.addLayout(form_layout)
        layout.addSpacing(10)
        layout.addLayout(button_layout)
        layout.addSpacing(15)
        layout.addWidget(self.graph_frame)
        layout.addItem(QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.setLayout(layout)

    def on_calculate(self):
        msg = QLabel(str(wolfram.evaluate("2+2")))
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet("color: #B0E0E6; font-size: 13px;")

        for i in reversed(range(self.graph_frame.layout().count())):
            widget = self.graph_frame.layout().itemAt(i).widget()
            if widget:
                widget.deleteLater()
        self.graph_frame.layout().addWidget(msg)

    def on_clear(self):
        for box in [self.alpha_input, self.beta_input, self.gamma_input,
                    self.delta_input, self.x0_input, self.y0_input]:
            box.clear()
        for i in reversed(range(self.graph_frame.layout().count())):
            widget = self.graph_frame.layout().itemAt(i).widget()
            if widget:
                widget.deleteLater()
        placeholder = QLabel("График появится здесь после расчёта")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #888888; font-style: italic;")
        self.graph_frame.layout().addWidget(placeholder)


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
        self.resize(800, 600)
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

