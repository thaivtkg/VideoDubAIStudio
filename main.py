import sys
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    # 1. Ép dùng Fusion Style để vô hiệu hóa Native UI của Windows
    app.setStyle("Fusion")

    # 2. Ép Font hệ thống chuẩn
    font = app.font()
    font.setFamily("Segoe UI")
    app.setFont(font)

    # 3. Đưa Style Sheet lên mức Global (Áp dụng cho toàn bộ app)
    app.setStyleSheet("""
        QMainWindow { background-color: #1E1E1E; color: white; }

        QMenuBar { background-color: #1E1E1E; color: white; border-bottom: 1px solid #333; }
        QMenuBar::item { background-color: transparent; padding: 4px 10px; color: white; }
        QMenuBar::item:selected { background-color: #3E3E42; color: white; }
        QMenuBar::item:pressed { background-color: #007ACC; color: white; }

        QMenu { background-color: #252526; color: white; border: 1px solid #333; }
        QMenu::item { padding: 5px 30px 5px 20px; color: white; }
        QMenu::item:selected { background-color: #007ACC; color: white; }

        QDockWidget { color: white; font-weight: bold; }
        QDockWidget::title { background-color: #252526; padding: 4px; text-align: center; }
        
        /* THÊM KHỐI NÀY ĐỂ HIỂN THỊ STATUS BAR RÕ RÀNG */
        QStatusBar { background-color: #007ACC; color: white; font-weight: bold; }
        QStatusBar::item { border: none; }
    """)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()