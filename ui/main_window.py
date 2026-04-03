from ui.ISLM_tab import ISLMTab
from ui.lorenz_tab import LorenzTab
from ui.lotka_volterra_tab import LotkaVolterraTab
from ui.competing_species_tab import CompetingSpeciesTab
from ui.placeholders import create_placeholder_tab
from core.database import get_all_calculations, clear_all
from ui.competing_species_tab import CompetingSpeciesTab
from ui.SIR_tab import SIRTab
from core.database import load_calculation
from datetime import datetime


from functools import partial

from PyQt6.QtCore import QTimer

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QSpacerItem,
    QSizePolicy, QTabWidget, QProgressBar, QMessageBox, QMainWindow, QMessageBox, QMenuBar, QApplication
)
from PyQt6.QtGui import QAction

from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.lotka_tab = None
        self.load_menu = None

    def init_ui(self):
        self.setWindowTitle("Симуляция динамических систем")
        self.resize(1200, 800)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Главный layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Создаем меню
        self.create_menu_bar()

        # Создаем вкладки
        tabs = QTabWidget()
        self.tabs = tabs
        self.lotka_tab = LotkaVolterraTab()
        self.competing_species_tab = CompetingSpeciesTab()
        self.SIR_tab = SIRTab()
        self.islm_tab = ISLMTab()
        self.lorenz_tab = LorenzTab()
        tabs.addTab(self.lotka_tab, "Лотка–Вольтерра")
        tabs.addTab(self.competing_species_tab, "Конкуренция видов")
        tabs.addTab(self.SIR_tab, "Распространение эпидемии")
        tabs.addTab(self.islm_tab, "IS-LM")
        tabs.addTab(self.lorenz_tab, "Аттрактор Лоренца")

        main_layout.addWidget(tabs)

        # Стили
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
            QMenuBar {
                background-color: #2E2E3F;
                color: white;
                padding: 4px;
            }
            QMenuBar::item {
                background-color: #2E2E3F;
                color: white;
                padding: 4px 10px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #3C8DAD;
            }
            QMenu {
                background-color: #2E2E3F;
                color: white;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #3C8DAD;
            }
        """)

    def create_menu_bar(self):
        self.menuBar()
        self.refresh_menu_bar()

    from datetime import datetime
    from functools import partial

    def refresh_menu_bar(self):
        """Красивое пересоздание меню с группировкой моделей."""

        new_bar = QMenuBar(self)
        self.setMenuBar(new_bar)

        # ========== ФАЙЛ ==========
        file_menu = new_bar.addMenu("📁 Файл")

        save_action = QAction("💾 Сохранить текущий расчет", self)
        save_action.triggered.connect(self.save_current_calculation)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        # -------- Загрузка --------
        self.load_menu = file_menu.addMenu("📂 Загрузить расчет")

        calculations = get_all_calculations()
        calculations.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        if not calculations:
            a = QAction("Нет сохранённых расчётов", self)
            a.setEnabled(False)
            self.load_menu.addAction(a)

        else:

            models = {}

            # группируем по моделям
            for calc in calculations:
                model = calc.get("model_name", "Модель")

                if model not in models:
                    models[model] = []

                models[model].append(calc)

            for model_name, calcs in models.items():

                model_menu = self.load_menu.addMenu(f"📊 {model_name}")

                for calc in calcs:

                    calc_id = calc["id"]

                    # ===== красивая дата =====
                    timestamp = calc.get("timestamp", "")

                    try:
                        dt = datetime.fromisoformat(timestamp)
                        timestamp = dt.strftime("%d.%m.%Y %H:%M")
                    except:
                        pass

                    # ===== параметры =====

                    params = []

                    # Лотка-Вольтерра
                    if "alpha" in calc:
                        params.append(f"α={calc['alpha']}")
                    if "beta" in calc:
                        params.append(f"β={calc['beta']}")
                    if "gamma" in calc:
                        params.append(f"γ={calc['gamma']}")
                    if "delta" in calc:
                        params.append(f"δ={calc['delta']}")

                    # Конкуренция видов
                    if "p" in calc:
                        params.append(f"p={calc['p']}")
                    if "s" in calc:
                        params.append(f"s={calc['s']}")
                    if "q" in calc:
                        params.append(f"q={calc['q']}")
                    if "t" in calc:
                        params.append(f"t={calc['t']}")

                    # ISLM
                    if "G" in calc:
                        params.append(f"G={calc['G']}")
                    if "Ms" in calc:
                        params.append(f"Ms={calc['Ms']}")
                    if "I0" in calc:
                        params.append(f"I₀={calc['I0']}")
                    if "MPC" in calc:
                        params.append(f"MPC={calc['MPC']}")

                    # Лоренц
                    if "sigma" in calc:
                        params.append(f"σ={calc['sigma']}")
                    if "rho" in calc:
                        params.append(f"ρ={calc['rho']}")

                    params_text = " ".join(params)

                    text = f"• {params_text} — {timestamp}"

                    action = QAction(text, self)
                    action.triggered.connect(partial(self.load_calculation, calc_id))

                    model_menu.addAction(action)

        file_menu.addSeparator()

        clear_history_action = QAction("🗑 Очистить всю историю", self)
        clear_history_action.triggered.connect(self.clear_all_history)
        file_menu.addAction(clear_history_action)

        # ========== ПОМОЩЬ ==========
        help_menu = new_bar.addMenu("❓ Помощь")

        about_action = QAction("ℹ️ О программе", self)
        about_action.triggered.connect(self.show_about)

        help_menu.addAction(about_action)

    def save_current_calculation(self):
        """Сохраняет текущий расчет"""

        current_tab = self.tabs.currentWidget()

        # Проверяем, поддерживает ли вкладка сохранение
        if hasattr(current_tab, "save_current_calculation"):

            success = current_tab.save_current_calculation()

            if success:
                QTimer.singleShot(0, self.refresh_menu_bar)

    def load_calculation(self, calc_id):
        """Загружает расчет по ID"""

        calc = load_calculation(calc_id)

        if not calc:
            QMessageBox.warning(self, "Ошибка", "Расчет не найден!")
            return

        model = calc.get("model_name")

        # ---------- ЛОТКА ВОЛЬТЕРРА ----------
        if model == "Лотка-Вольтерра":

            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)

                if isinstance(tab, LotkaVolterraTab):
                    self.tabs.setCurrentIndex(i)

                    if tab.load_calculation_by_id(calc_id):
                        QMessageBox.information(self, "Загрузка", "Расчет успешно загружен!")
                    return

        # ---------- КОНКУРЕНЦИЯ ВИДОВ ----------
        if model == "Конкуренция видов":

            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)

                if isinstance(tab, CompetingSpeciesTab):
                    self.tabs.setCurrentIndex(i)

                    if tab.load_calculation_by_id(calc_id):
                        QMessageBox.information(self, "Загрузка", "Расчет успешно загружен!")

                    return

                # ---------- ЭПИДЕМИЯ SEIR ----------
        if model == "Модель эпидемии SEIR":
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if isinstance(tab, SIRTab):
                    self.tabs.setCurrentIndex(i)
                    if tab.load_calculation_by_id(calc_id):
                        QMessageBox.information(self, "Загрузка", "Расчет успешно загружен!")
                    return

        # ----------- ISLM -------------
        if model == "Макроэкономическая модель IS-LM":
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if isinstance(tab, ISLMTab):
                    self.tabs.setCurrentIndex(i)
                    if tab.load_calculation_by_id(calc_id):
                        QMessageBox.information(self, "Загрузка", "Расчет успешно загружен!")
                    return

        if model == "Система Лоренца":
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                # Проверяем, что это именно вкладка Лоренца
                if isinstance(tab, LorenzTab):
                    self.tabs.setCurrentIndex(i)
                    if tab.load_calculation_by_id(calc_id):
                        QMessageBox.information(self, "Загрузка", "Расчет успешно загружен!")
                    return

        QMessageBox.warning(self, "Ошибка", "Не удалось загрузить расчет!")

    def clear_all_history(self):
        reply = QMessageBox.question(
            self,
            'Подтверждение удаления',
            'Вы уверены, что хотите удалить ВСЕ сохраненные расчеты?\nЭто действие нельзя отменить!',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            clear_all()

            QTimer.singleShot(0, self.refresh_menu_bar)

            QMessageBox.information(self, "Очистка", "Вся история расчетов удалена!")

    def show_about(self):
        """Показывает информацию о программе"""
        QMessageBox.information(self, "О программе",
                                "Симулятор динамических систем\n\n"
                                "Версия 1.0\n"
                                "Лотка-Вольтерра: модель хищник-жертва\n\n"
                                "Функции:\n"


                                "• Расчет системы дифферкуенциальных уравнений через Wolfram\n"
                                "• Визуализация графиков и анимаций\n"
                                "• Сохранение и загрузка расчетов")

    def create_placeholder_tab(self, title):
        """Создает вкладку-заглушку"""
        tab = QWidget()
        layout = QVBoxLayout()
        label = QLabel(f"<b>{title}</b><br><br>Эта модель будет добавлена позже.")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #AAAAAA; font-size: 14px; font-style: italic;")
        layout.addWidget(label)
        tab.setLayout(layout)
        return tab