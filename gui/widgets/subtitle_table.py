from PySide6.QtCore import QAbstractTableModel, Qt
from PySide6.QtWidgets import QHeaderView, QTableView


class SubtitleTableModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data or []
        # THÊM 2 CỘT MỚI: Voice và Audio
        self.headers = ["ID", "Start", "End", "Text", "Voice", "Audio"]

    def data(self, index, role):
        if not index.isValid() or index.row() < 0 or index.row() >= len(self._data):
            return None

        row = self._data[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0: return row.id
            elif col == 1: return f"{row.start_time:.3f}"
            elif col == 2: return f"{row.end_time:.3f}"
            elif col == 3: return row.text
            elif col == 4: return row.voice_id # Hiển thị tên giọng
            elif col == 5:
                # Chuyển đổi trạng thái thành Icon/Symbol
                if row.audio_status == "generated": return "✓"
                elif row.audio_status == "generating": return "◷"
                elif row.audio_status == "error": return "⚠"
                else: return "○"

        # (Tùy chọn) Đổi màu chữ cho cột Audio Status để dễ nhìn
        elif role == Qt.ForegroundRole and index.column() == 5:
            from PySide6.QtGui import QColor
            if row.audio_status == "generated": return QColor("#4CAF50") # Xanh lá
            elif row.audio_status == "error": return QColor("#F44336")   # Đỏ
            elif row.audio_status == "generating": return QColor("#FFC107") # Vàng

        return None

    def rowCount(self, index=None): return len(self._data)
    def columnCount(self, index=None): return len(self.headers)

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled

        flags = super().flags(index)
        if index.column() in (1, 2, 3, 4):
            flags |= Qt.ItemIsEditable
        return flags

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False

        row = self._data[index.row()]
        col = index.column()

        if col == 1:
            try:
                row.start_time = float(value)
            except (TypeError, ValueError):
                return False
        elif col == 2:
            try:
                row.end_time = float(value)
            except (TypeError, ValueError):
                return False
        elif col == 3:
            row.text = str(value)
        elif col == 4:
            row.voice_id = str(value)
        else:
            return False

        self.dataChanged.emit(index, index, [role])
        return True

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
        
        # Ép độ rộng các cột cho đẹp
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch) # Cột Text giãn hết cỡ
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents) # Cột ID
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents) # Cột Voice
        self.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents) # Cột Audio
        
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setAlternatingRowColors(True)
        self.setStyleSheet("""
            QTableView { 
                background-color: #1E1E1E; 
                alternate-background-color: #2D2D30; /* THÊM DÒNG NÀY: Định nghĩa màu cho dòng xen kẽ */
                color: white; 
                gridline-color: #333; 
            }
            QHeaderView::section { 
                background-color: #252526; 
                color: white; 
                padding: 4px; 
                border: 1px solid #333; 
            }
        """)