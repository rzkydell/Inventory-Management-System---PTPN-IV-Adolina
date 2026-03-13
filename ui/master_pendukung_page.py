import sqlite3
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, 
    QHeaderView, QFrame, QTabWidget, QAbstractItemView, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon
from database.connection import get_connection

class MasterPendukungPage(QWidget):
    """
    Halaman Master Data Pendukung (Kategori & Lokasi).
    Didesain profesional untuk sinkronisasi database PTPN IV.
    """
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.refresh_all_data()

    def showEvent(self, event):
        """Auto-refresh saat tab dibuka"""
        super().showEvent(event)
        self.refresh_all_data() 

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- TAB WIDGET STYLE (Modern Slate Blue) ---
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #e2e8f0; background: white; border-radius: 0px; top: -1px; }
            QTabBar::tab { 
                padding: 14px 40px; font-weight: 600; color: #64748b; 
                background: #f1f5f9; border: 1px solid #e2e8f0;
                border-bottom: none; border-top-left-radius: 10px; border-top-right-radius: 10px;
                margin-right: 5px;
            }
            QTabBar::tab:selected { background: white; color: #3b82f6; border-bottom: 3px solid #3b82f6; }
            QTabBar::tab:hover { background: #e2e8f0; color: #1e293b; }
        """)

        # Tab 1: KATEGORI
        self.tab_kategori = QWidget()
        self.setup_kategori_ui()
        self.tabs.addTab(self.tab_kategori, "🏷️ KATEGORI BARANG")

        # Tab 2: LOKASI
        self.tab_lokasi = QWidget()
        self.setup_lokasi_ui()
        self.tabs.addTab(self.tab_lokasi, "📍 LOKASI RAK / SLOT")

        main_layout.addWidget(self.tabs)

    def setup_kategori_ui(self):
        layout = QVBoxLayout(self.tab_kategori)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        btn_add = QPushButton("➕ TAMBAH KATEGORI BARU")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setStyleSheet("""
            QPushButton { background-color: #3b82f6; color: white; font-weight: bold; padding: 12px 25px; border-radius: 8px; }
            QPushButton:hover { background-color: #2563eb; }
        """)
        btn_add.clicked.connect(self.tambah_kategori_dialog)
        layout.addWidget(btn_add, 0, Qt.AlignRight)

        self.table_kat = self.create_styled_table(["NO", "NAMA KATEGORI", "AKSI TINDAKAN"])
        layout.addWidget(self.table_kat)

    def setup_lokasi_ui(self):
        layout = QVBoxLayout(self.tab_lokasi)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        btn_add = QPushButton("➕ TAMBAH LOKASI BARU")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setStyleSheet("""
            QPushButton { background-color: #10b981; color: white; font-weight: bold; padding: 12px 25px; border-radius: 8px; }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_add.clicked.connect(self.tambah_lokasi_dialog)
        layout.addWidget(btn_add, 0, Qt.AlignRight)

        self.table_lok = self.create_styled_table(["NO", "NAMA LOKASI PENYIMPANAN", "AKSI TINDAKAN"])
        layout.addWidget(self.table_lok)

    def create_styled_table(self, headers):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed); table.setColumnWidth(0, 70) 
        header.setSectionResizeMode(1, QHeaderView.Stretch)                             
        header.setSectionResizeMode(2, QHeaderView.Fixed); table.setColumnWidth(2, 200) 
        
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(50) 
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        
        table.setStyleSheet("""
            QTableWidget { background-color: white; border: 1px solid #e2e8f0; border-radius: 16px; color: #000000; font-size: 14px; }
            QHeaderView::section { 
                background-color: #f8fafc; color: #000000; font-weight: bold; 
                padding: 15px; border: none; border-bottom: 2px solid #e2e8f0; 
                text-transform: uppercase; font-size: 12px;
            }
        """)
        self.apply_shadow(table)
        return table

    def apply_shadow(self, widget):
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(20); shadow.setXOffset(0); shadow.setYOffset(4); shadow.setColor(QColor(0, 0, 0, 20))
        widget.setGraphicsEffect(shadow)

    def create_action_buttons(self, table, row_idx, data_id, data_name, type):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 5, 5, 5); layout.setSpacing(10); layout.setAlignment(Qt.AlignCenter)
        
        btn_edit = QPushButton("✏️ EDIT")
        btn_del = QPushButton("🗑️ HAPUS")
        
        # Style Sinkron Dashboard Biru & Merah
        btn_edit.setStyleSheet("""
            QPushButton { background-color: #ebf5ff; color: #2563eb; border: 1px solid #bfdbfe; border-radius: 6px; padding: 5px 15px; font-weight: bold; font-size: 11px; }
            QPushButton:hover { background-color: #dbeafe; }
        """)
        btn_del.setStyleSheet("""
            QPushButton { background-color: #fef2f2; color: #dc2626; border: 1px solid #fecaca; border-radius: 6px; padding: 5px 15px; font-weight: bold; font-size: 11px; }
            QPushButton:hover { background-color: #fee2e2; }
        """)

        if type == "kat":
            btn_edit.clicked.connect(lambda: self.edit_kategori(data_id, data_name))
            btn_del.clicked.connect(lambda: self.hapus_kategori(data_id, data_name))
        else:
            btn_edit.clicked.connect(lambda: self.edit_lokasi(data_id, data_name))
            btn_del.clicked.connect(lambda: self.hapus_lokasi(data_id, data_name))
            
        layout.addWidget(btn_edit)
        layout.addWidget(btn_del)
        table.setCellWidget(row_idx, 2, container)

    def tambah_kategori_dialog(self):
        dialog = QInputDialog(self)
        dialog.setWindowTitle("➕ Tambah Kategori")
        dialog.setLabelText("Masukkan Nama Kategori baru:")
        dialog.setOkButtonText("Tambah"); dialog.setCancelButtonText("Batal")
        dialog.setStyleSheet("QInputDialog { background-color: white; } QLabel { color: black; font-weight: bold; } QLineEdit { color: black; background: #f8fafc; border: 1px solid #3b82f6; padding: 8px; } QPushButton { color: black; font-weight: bold; background-color: #f1f5f9; border: 1px solid #cbd5e1; padding: 5px 15px; }")
        
        if dialog.exec() == QInputDialog.Accepted:
            nama = dialog.textValue().strip().title()
            if nama:
                try:
                    conn = get_connection(); cursor = conn.cursor()
                    cursor.execute("INSERT INTO kategori (nama_kategori) VALUES (?)", (nama,))
                    conn.commit(); conn.close()
                    self.load_data_kategori()
                    self.show_notif("Berhasil", f"Kategori '{nama}' berhasil ditambahkan.")
                except Exception as e: self.show_notif("Gagal", f"Error: {e}", is_error=True)

    def edit_kategori(self, id_k, nama_lama):
        dialog = QInputDialog(self)
        dialog.setWindowTitle("✏️ Edit Kategori")
        dialog.setLabelText(f"Ubah Nama Kategori '{nama_lama}' menjadi:")
        dialog.setTextValue(nama_lama)
        dialog.setOkButtonText("Update"); dialog.setCancelButtonText("Batal")
        dialog.setStyleSheet("QInputDialog { background-color: white; } QLabel { color: black; font-weight: bold; } QLineEdit { color: black; background: #f8fafc; border: 1px solid #3b82f6; padding: 8px; } QPushButton { color: black; font-weight: bold; background-color: #f1f5f9; border: 1px solid #cbd5e1; padding: 5px 15px; }")
        
        if dialog.exec() == QInputDialog.Accepted:
            baru = dialog.textValue().strip().title()
            if baru and baru != nama_lama:
                conn = get_connection(); cursor = conn.cursor()
                cursor.execute("UPDATE kategori SET nama_kategori = ? WHERE id_kategori = ?", (baru, id_k))
                conn.commit(); conn.close(); self.load_data_kategori()
                self.show_notif("Berhasil", f"Kategori diperbarui menjadi '{baru}'.")

    def hapus_kategori(self, id_k, nama):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Konfirmasi Hapus")
        msg.setText(f"Hapus kategori '{nama}'?")
        msg.setInformativeText("PERHATIAN: Barang dengan kategori ini akan kehilangan referensinya.")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setStyleSheet("QMessageBox { background-color: white; } QLabel { color: black; font-size: 13px; } QPushButton { color: black; font-weight: bold; background-color: #f1f5f9; border: 1px solid #cbd5e1; min-width: 80px; padding: 5px; }")
        
        if msg.exec() == QMessageBox.Yes:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("DELETE FROM kategori WHERE id_kategori = ?", (id_k,))
            conn.commit(); conn.close(); self.load_data_kategori()

    def load_data_kategori(self):
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("SELECT id_kategori, nama_kategori FROM kategori ORDER BY id_kategori DESC")
            rows = cursor.fetchall(); self.table_kat.setRowCount(0)
            for i, row in enumerate(rows):
                self.table_kat.insertRow(i)
                no = QTableWidgetItem(str(i + 1)); no.setTextAlignment(Qt.AlignCenter)
                self.table_kat.setItem(i, 0, no)
                self.table_kat.setItem(i, 1, QTableWidgetItem(str(row[1])))
                self.create_action_buttons(self.table_kat, i, row[0], row[1], "kat")
            conn.close()
        except: pass

    def tambah_lokasi_dialog(self):
        dialog = QInputDialog(self)
        dialog.setWindowTitle("➕ Tambah Lokasi")
        dialog.setLabelText("Masukkan Nama Lokasi baru:")
        dialog.setOkButtonText("Tambah"); dialog.setCancelButtonText("Batal")
        dialog.setStyleSheet("QInputDialog { background-color: white; } QLabel { color: black; font-weight: bold; } QLineEdit { color: black; background: #f8fafc; border: 1px solid #cbd5e1; padding: 8px; } QPushButton { color: black; font-weight: bold; background-color: #f1f5f9; border: 1px solid #cbd5e1; padding: 5px 15px; }")
        
        if dialog.exec() == QInputDialog.Accepted:
            nama = dialog.textValue().strip().title()
            if nama:
                try:
                    conn = get_connection(); cursor = conn.cursor()
                    cursor.execute("INSERT INTO lokasi (nama_lokasi) VALUES (?)", (nama,))
                    conn.commit(); conn.close()
                    self.load_data_lokasi()
                    self.show_notif("Berhasil", f"Lokasi '{nama}' berhasil didaftarkan.")
                except Exception as e: self.show_notif("Gagal", f"Error: {e}", is_error=True)

    def edit_lokasi(self, id_l, nama_lama):
        dialog = QInputDialog(self)
        dialog.setWindowTitle("✏️ Edit Lokasi")
        dialog.setLabelText(f"Ubah Nama Lokasi '{nama_lama}' menjadi:")
        dialog.setTextValue(nama_lama)
        dialog.setOkButtonText("Update"); dialog.setCancelButtonText("Batal")
        dialog.setStyleSheet("QInputDialog { background-color: white; } QLabel { color: black; } QLineEdit { color: black; } QPushButton { color: black; font-weight: bold; background-color: #f1f5f9; border: 1px solid #cbd5e1; padding: 5px 15px; }")
        
        if dialog.exec() == QInputDialog.Accepted:
            baru = dialog.textValue().strip().title()
            if baru:
                conn = get_connection(); cursor = conn.cursor()
                cursor.execute("UPDATE lokasi SET nama_lokasi = ? WHERE id_lokasi = ?", (baru, id_l))
                conn.commit(); conn.close(); self.load_data_lokasi()
                self.show_notif("Berhasil", f"Lokasi diubah menjadi '{baru}'.")

    def hapus_lokasi(self, id_l, nama):
        msg = QMessageBox(self)
        msg.setWindowTitle("Konfirmasi Hapus")
        msg.setText(f"Hapus lokasi '{nama}'?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setStyleSheet("QMessageBox { background-color: white; } QLabel { color: black; } QPushButton { color: black; font-weight: bold; background-color: #f1f5f9; border: 1px solid #cbd5e1; min-width: 80px; padding: 5px; }")
        
        if msg.exec() == QMessageBox.Yes:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("DELETE FROM lokasi WHERE id_lokasi = ?", (id_l,))
            conn.commit(); conn.close(); self.load_data_lokasi()

    def load_data_lokasi(self):
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("SELECT id_lokasi, nama_lokasi FROM lokasi ORDER BY id_lokasi DESC")
            rows = cursor.fetchall(); self.table_lok.setRowCount(0)
            for i, row in enumerate(rows):
                self.table_lok.insertRow(i)
                no = QTableWidgetItem(str(i + 1)); no.setTextAlignment(Qt.AlignCenter)
                self.table_lok.setItem(i, 0, no)
                self.table_lok.setItem(i, 1, QTableWidgetItem(str(row[1])))
                self.create_action_buttons(self.table_lok, i, row[0], row[1], "lok")
            conn.close()
        except: pass

    def show_notif(self, title, text, is_error=False):
        msg = QMessageBox(self)
        msg.setWindowTitle(title); msg.setText(text)
        msg.setIcon(QMessageBox.Critical if is_error else QMessageBox.Information)
        # Style Teks Hitam Pekat & Tombol Jelas
        msg.setStyleSheet("""
            QMessageBox { background-color: white; } 
            QLabel { color: black; font-size: 13px; font-weight: normal; } 
            QPushButton { color: black; font-weight: bold; background-color: #f1f5f9; border: 1px solid #cbd5e1; min-width: 70px; padding: 5px; }
        """)
        msg.exec()

    def refresh_all_data(self):
        self.load_data_kategori()
        self.load_data_lokasi()