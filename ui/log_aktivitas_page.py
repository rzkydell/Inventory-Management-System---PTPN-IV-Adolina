import os
import sqlite3
import csv
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QFileDialog, QMessageBox, QFrame,
    QAbstractItemView, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from database.connection import get_connection

class LogAktivitasPage(QWidget):
    """
    Halaman Rekam Jejak / Audit Log Aktivitas Pengguna.
    Menampilkan histori tindakan yang dilakukan di dalam sistem.
    """
    def __init__(self):
        super().__init__()
        self.init_ui()

    def showEvent(self, event):
        """Refresh logs otomatis saat halaman dibuka"""
        super().showEvent(event)
        self.load_logs()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # --- MANDATORY SCROLL AREA ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #f8fafc; }")
        
        container = QWidget()
        container.setStyleSheet("background-color: #f8fafc;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        self.setStyleSheet("""
            QWidget { font-family: 'Segoe UI', Arial; font-size: 13px; color: #1e293b; }
            QLabel { color: #1e293b; font-weight: 700; }
        """)

        # --- TOP ACTION BAR ---
        top_bar_card = QFrame()
        top_bar_card.setStyleSheet("background-color: white; border-radius: 16px; border: 1px solid #e2e8f0;")
        self.apply_shadow(top_bar_card)
        top_bar = QHBoxLayout(top_bar_card)
        
        lbl_title = QLabel("🕵️ RIWAYAT LOG AKTIVITAS SISTEM")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #0f172a;")
        
        self.btn_refresh = QPushButton("🔄 SEGARKAN")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setStyleSheet("""
            QPushButton { background-color: #3b82f6; color: white; font-weight: bold; padding: 8px 15px; border-radius: 8px; font-size: 11px; }
            QPushButton:hover { background-color: #2563eb; }
        """)
        self.btn_refresh.clicked.connect(self.load_logs)

        self.btn_export = QPushButton("📊 EKSPOR CSV")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setStyleSheet("""
            QPushButton { background-color: #10b981; color: white; font-weight: bold; padding: 8px 15px; border-radius: 8px; font-size: 11px; }
            QPushButton:hover { background-color: #059669; }
        """)
        self.btn_export.clicked.connect(self.export_csv)

        top_bar.addWidget(lbl_title)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_refresh)
        top_bar.addWidget(self.btn_export)
        layout.addWidget(top_bar_card)

        # --- TABLE LOG ---
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Waktu / Timestamp", "User", "Aktivitas System"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget { background: white; border-radius: 16px; border: 1px solid #e2e8f0; color: #1e293b; gridline-color: #f1f5f9; }
            QHeaderView::section { background: #f8fafc; color: #475569; font-weight: bold; padding: 12px; border: none; border-bottom: 2px solid #e2e8f0; }
            QTableWidget::item { padding: 8px; }
            QTableWidget::item:selected { background-color: #eff6ff; color: #1e293b; }
        """)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 160)
        self.table.setColumnWidth(2, 100)
        
        self.apply_shadow(self.table)
        layout.addWidget(self.table)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def apply_shadow(self, widget):
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(20); shadow.setXOffset(0); shadow.setYOffset(4); shadow.setColor(QColor(0, 0, 0, 20))
        widget.setGraphicsEffect(shadow)

    def load_logs(self):
        try:
            conn = get_connection()
            if not conn: return
            
            cursor = conn.cursor()
            cursor.execute("SELECT id, waktu, user, aktivitas FROM log_aktivitas ORDER BY id DESC LIMIT 500")
            rows = cursor.fetchall()
            
            self.table.setRowCount(0)
            for i, r in enumerate(rows):
                self.table.insertRow(i)
                self.table.setItem(i, 0, QTableWidgetItem(str(r[0])))
                self.table.setItem(i, 1, QTableWidgetItem(str(r[1])))
                self.table.setItem(i, 2, QTableWidgetItem(str(r[2])))
                
                act_item = QTableWidgetItem(str(r[3]))
                if "HAPUS" in str(r[3]).upper() or "ERROR" in str(r[3]).upper():
                    act_item.setForeground(QColor("#ef4444"))
                elif "TAMBAH" in str(r[3]).upper():
                    act_item.setForeground(QColor("#10b981"))
                
                self.table.setItem(i, 3, act_item)
                
                # Center align first 3 columns
                self.table.item(i, 0).setTextAlignment(Qt.AlignCenter)
                self.table.item(i, 1).setTextAlignment(Qt.AlignCenter)
                self.table.item(i, 2).setTextAlignment(Qt.AlignCenter)
            
            conn.close()
        except Exception as e:
            print(f"Gagal memuat log: {e}")

    def export_csv(self):
        if self.table.rowCount() == 0: return
        
        path, _ = QFileDialog.getSaveFileName(self, "Simpan Log CSV", "Log_Aktivitas.csv", "CSV Files (*.csv)")
        if path:
            try:
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["ID", "Waktu", "User", "Aktivitas"])
                    for r in range(self.table.rowCount()):
                        writer.writerow([self.table.item(r, c).text() for c in range(4)])
                
                QMessageBox.information(self, "Sukses", f"Log berhasil diekspor ke {path}")
            except Exception as e:
                QMessageBox.critical(self, "Gagal", f"Error ekspor: {e}")
