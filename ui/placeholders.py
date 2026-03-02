from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

def create_placeholder_tab(title):
    tab = QWidget()
    layout = QVBoxLayout()
    label = QLabel(f"<b>{title}</b><br><br>Эта модель будет добавлена позже.")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)
    tab.setLayout(layout)
    return tab