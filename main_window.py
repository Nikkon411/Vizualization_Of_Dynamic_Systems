# main_window.py
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QMenuBar, QMenu,
    QTabWidget, QLabel, QMessageBox, QApplication
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

from database import get_all_calculations, clear_all_history
from LotkaVolteraTab import LotkaVolterraTab

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
        tabs.addTab(self.lotka_tab, "Лотка–Вольтерра")
        tabs.addTab(self.create_placeholder_tab("Маятник"), "Маятник")
        tabs.addTab(self.create_placeholder_tab("Система Лоренца"), "Система Лоренца")
        tabs.addTab(self.create_placeholder_tab("Химическая реакция"), "Химическая реакция")

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

    def refresh_menu_bar(self):
        """Полное безопасное пересоздание меню (исправляет проблему старых QAction)."""

        # Полностью пересоздаём меню-бар (не очищаем, а создаём новый объект)
        new_bar = QMenuBar(self)
        self.setMenuBar(new_bar)

        # ========== ФАЙЛ ==========
        file_menu = new_bar.addMenu("📁 Файл")

        save_action = QAction("💾 Сохранить текущий расчет", self)
        save_action.triggered.connect(self.save_current_calculation)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        # ---- Загрузить расчет ----
        self.load_menu = file_menu.addMenu("📂 Загрузить расчет")

        calculations = get_all_calculations()
        calculations.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        if not calculations:
            a = QAction("Нет сохранённых расчётов", self)
            a.setEnabled(False)
            self.load_menu.addAction(a)
        else:
            for calc in calculations:
                calc_id = calc['id']
                alpha = calc['alpha']
                beta = calc['beta']
                timestamp = calc['timestamp']

                action = QAction(f"α={alpha}, β={beta} — {timestamp}", self)
                action.triggered.connect(lambda _, cid=calc_id: self.load_calculation(cid))
                self.load_menu.addAction(action)

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
        # Получаем текущую активную вкладку
        current_tab = self.tabs.currentWidget()

        # Проверяем, является ли текущая вкладка LotkaVolterraTab
        if isinstance(current_tab, LotkaVolterraTab):
            success = current_tab.save_current_calculation()
            if success:
                # Обновляем меню
                self.refresh_menu_bar()
                self.menuBar().update()

    def load_calculation(self, calc_id):
        """Загружает расчет по ID"""
        # Получаем текущую активную вкладку
        current_tab = self.tabs.currentWidget()

        # Проверяем, является ли текущая вкладка LotkaVolterraTab
        if isinstance(current_tab, LotkaVolterraTab):
            if current_tab.load_calculation_by_id(calc_id):
                # 1. Принудительно обновляем все графики
                for _ in range(3):
                    QApplication.processEvents()

                # 2. Создаем НЕ МОДАЛЬНОЕ сообщение
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Загрузка")
                msg_box.setText("Расчет успешно загружен!")
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

                # Ключевой момент: окно НЕ блокирует основной интерфейс
                msg_box.setModal(False)

                # Показываем окно
                msg_box.show()


            else:
                # Для ошибок можно оставить обычный QMessageBox
                QMessageBox.warning(self, "Ошибка", "Не удалось загрузить расчет!")


    def clear_all_history(self):
        """Очищает всю историю расчетов"""
        reply = QMessageBox.question(
            self, 'Подтверждение удаления',
            'Вы уверены, что хотите удалить ВСЕ сохраненные расчеты?\nЭто действие нельзя отменить!',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Удаляем все записи из базы данных
            clear_all_history()

            # Обновляем меню загрузки
            self.refresh_menu_bar()
            self.menuBar().update()

            QMessageBox.information(self, "Очистка", "Вся история расчетов удалена!")

    def show_about(self):
        """Показывает информацию о программе"""
        QMessageBox.information(self, "О программе",
                                "Симулятор динамических систем\n\n"
                                "Версия 1.0\n"
                                "Лотка-Вольтерра: модель хищник-жертва\n\n"
                                "Функции:\n"
                                "• Расчет системы дифференциальных уравнений через Wolfram\n"
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