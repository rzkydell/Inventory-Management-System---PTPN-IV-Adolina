import os
import sys
import shutil
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QFileDialog, QMessageBox, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

class PengaturanPage(QWidget):
    """
    Halaman Pengaturan Sistem (Backup & Restore).
    """
    def __init__(self):
        super().__init__()
        self.init_ui()

    def get_db_path(self):
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Pengecekan path yang benar untuk database
        db_path = os.path.join(base_dir, "database", "inventory.db")
        if not os.path.exists(db_path):
            db_path = os.path.join(base_dir, "inventory.db")
        return db_path

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

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

        # --- SECTION 1: SYSTEM INFO ---
        info_card = QFrame()
        info_card.setStyleSheet("background-color: white; border-radius: 16px; border: 1px solid #e2e8f0;")
        self.apply_shadow(info_card)
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 20, 20, 20)

        info_title = QLabel("🛡️ KEAMANAN & SISTEM")
        info_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #1e293b;")
        info_desc = QLabel("Jaga keamanan data Anda dengan melakukan backup (pencadangan) database secara berkala. Simpan file cadangan Anda di Flashdisk atau Cloud/Drive untuk mencegah resiko kehilangan data permanen akibat kerusakan komputer.")
        info_desc.setWordWrap(True)
        info_desc.setStyleSheet("color: #64748b; margin-top: 5px;")
        
        info_layout.addWidget(info_title)
        info_layout.addWidget(info_desc)
        layout.addWidget(info_card)

        # --- SECTION 2: BACKUP & RESTORE ---
        db_card = QFrame()
        db_card.setStyleSheet("background-color: white; border-radius: 16px; border: 1px solid #e2e8f0;")
        self.apply_shadow(db_card)
        db_layout = QVBoxLayout(db_card)
        db_layout.setContentsMargins(20, 20, 20, 20)
        db_layout.setSpacing(20)

        # ACTION: BACKUP
        btn_backup = QPushButton("💾 BACKUP SEKARANG (CADANGKAN)")
        btn_backup.setCursor(Qt.PointingHandCursor)
        btn_backup.setFixedHeight(60)
        btn_backup.setStyleSheet("""
            QPushButton { background-color: #10b981; color: white; font-weight: bold; font-size: 14px; border-radius: 8px; }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_backup.clicked.connect(self.backup_database)
        db_layout.addWidget(btn_backup)

        db_separator = QFrame()
        db_separator.setFrameShape(QFrame.HLine)
        db_separator.setStyleSheet("color: #e2e8f0;")
        db_layout.addWidget(db_separator)

        # ACTION: RESTORE
        warning_lbl = QLabel("⚠️ PERHATIAN: Memulihkan (Restore) database akan menimpa seluruh data saat ini! Lakukan dengan hati-hati.")
        warning_lbl.setStyleSheet("color: #ef4444; font-size: 12px;")
        db_layout.addWidget(warning_lbl)

        btn_restore = QPushButton("🔄 RESTORE (PULIHKAN DATA)")
        btn_restore.setCursor(Qt.PointingHandCursor)
        btn_restore.setFixedHeight(60)
        btn_restore.setStyleSheet("""
            QPushButton { background-color: #ef4444; color: white; font-weight: bold; font-size: 14px; border-radius: 8px; }
            QPushButton:hover { background-color: #dc2626; }
        """)
        btn_restore.clicked.connect(self.restore_database)
        db_layout.addWidget(btn_restore)

        layout.addWidget(db_card)
        layout.addStretch()

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def apply_shadow(self, widget):
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(20); shadow.setXOffset(0); shadow.setYOffset(4); shadow.setColor(QColor(0, 0, 0, 20))
        widget.setGraphicsEffect(shadow)

    def show_notif(self, title, text, is_error=False, is_info=False):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        if is_error:
            msg.setIcon(QMessageBox.Critical)
        elif is_info:
            msg.setIcon(QMessageBox.Information)
        msg.setStyleSheet("QMessageBox { background-color: white; } QLabel { color: black; font-size: 13px; } QPushButton { color: black; font-weight: bold; min-width: 70px; }")
        msg.exec()

    def backup_database(self):
        db_path = self.get_db_path()
        if not os.path.exists(db_path):
            self.show_notif("Gagal", "File database aktif tidak ditemukan!", is_error=True)
            return
            
        default_name = f"backup_inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        file_path, _ = QFileDialog.getSaveFileName(self, "Simpan File Backup Data", default_name, "Database Files (*.db)")
        
        if file_path:
            try:
                shutil.copy2(db_path, file_path)
                self.show_notif("Berhasil", f"Database berhasil dicadangkan ke:\n{file_path}", is_info=True)
            except Exception as e:
                self.show_notif("Gagal", f"Terjadi kesalahan saat mencadangkan: {e}", is_error=True)

    def restore_database(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Peringatan Restore")
        msg.setText("APAKAH ANDA YAKIN INGIN MEMULIHKAN DATA?\n\nSeluruh data (stok, riwayat, dll) yang tidak ada di dalam file cadangan akan hilang secara permanen dan tertimpa!")
        msg.setIcon(QMessageBox.Warning)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setStyleSheet("QMessageBox { background-color: white; } QLabel { color: black; font-size: 12px; } QPushButton { color: black; min-width: 70px; font-weight: bold; }")
        
        if msg.exec() == QMessageBox.Yes:
            file_path, _ = QFileDialog.getOpenFileName(self, "Pilih File Database Cadangan (.db)", "", "Database Files (*.db)")
            if file_path:
                db_path = self.get_db_path()
                try:
                    # Tutup koneksi jika sewaktu-waktu ada koneksi lokal belum nutup
                    shutil.copy2(file_path, db_path)
                    self.show_notif("Restore Selesai", "Database berhasil dipulihkan!\nSilakan Muat Ulang atau Res-Start Aplikasinya jika ada data yang tidak sinkron.", is_info=True)
                except Exception as e:
                    self.show_notif("Gagal", f"Gagal memulihkan database: {e}", is_error=True)
