from PySide6.QtWidgets import QTableView, QHeaderView
from PySide6.QtCore import QAbstractTableModel, Qt


class SubtitleTableModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data or []
        self.headers = ["ID", "Start", "End", "Text"]

    def data(self, index, role):
        if role == Qt.DisplayRole:
            row = self._data[index.row()]
            col = index.column()
            if col == 0:
                return row.id
            elif col == 1:
                return f"{row.start_time:.3f}"
            elif col == 2:
                return f"{row.end_time:.3f}"
            elif col == 3:
                return row.text
        return None

    def rowCount(self, index=None):
        return len(self._data)

    def columnCount(self, index=None):
        return len(self.headers)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]
        return None

    def update_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()


class SubtitleTableWidget(QTableView):
    def __init__(self):
        super().__init__()
        self.model = SubtitleTableModel()
        self.setModel(self.model)

        # Cấu hình giao diện bảng
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setAlternatingRowColors(True)
        self.setStyleSheet("""
            QTableView { background-color: #1E1E1E; color: white; gridline-color: #333; }
            QHeaderView::section { background-color: #252526; color: white; padding: 4px; border: 1px solid #333; }
        """)