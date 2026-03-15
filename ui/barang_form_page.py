import os
import sqlite3
import cv2
import winsound
import sys
from pyzbar import pyzbar
from barcode import Code128
from barcode.writer import ImageWriter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QMessageBox, 
    QFrame, QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from database.connection import get_connection, catat_log
from datetime import datetime

class BarangFormPage(QWidget):
    """
    Halaman Form khusus untuk Tambah/Edit Barang.
    Didesain untuk kenyamanan input data pada layar kecil.
    """
    barang_saved = Signal()  # Signal untuk memberitahu MasterBarangPage agar refresh data
    back_requested = Signal() # Signal untuk kembali ke list

    def __init__(self):
        super().__init__()
        self.id_barang_aktif = None
        self.init_ui()
        self.load_kategori()
        self.load_lokasi()

    def init_ui(self):
        # Base background
        self.setStyleSheet("background-color: #f8fafc;")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Content Area with Centering
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setAlignment(Qt.AlignHCenter)

        # Centered Wrapper (Max Width: 650px)
        self.wrapper = QFrame()
        self.wrapper.setFixedWidth(650)
        self.wrapper.setStyleSheet("background: transparent; border: none;")
        wrapper_layout = QVBoxLayout(self.wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(25)

        # --- HEADER ---
        header_widget = QWidget()
        h_layout = QHBoxLayout(header_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        
        header_text_container = QWidget()
        header_text_layout = QVBoxLayout(header_text_container)
        header_text_layout.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel("TAMBAH BARANG BARU")
        self.title_label.setStyleSheet("color: #000000; font-size: 24px; font-weight: 800; border: none;")
        subtitle = QLabel("Lengkapi informasi detail untuk inventaris baru.")
        subtitle.setStyleSheet("color: #000000; font-size: 13px; border: none;")
        header_text_layout.addWidget(self.title_label)
        header_text_layout.addWidget(subtitle)
        
        h_layout.addWidget(header_text_container)
        h_layout.addStretch()
        wrapper_layout.addWidget(header_widget)

        # --- FORM CARD ---
        self.form_card = QFrame()
        self.form_card.setStyleSheet("""
            QFrame { background-color: white; border-radius: 20px; border: 1px solid #e2e8f0; }
            QLabel { color: #000000; font-weight: bold; font-size: 12px; text-transform: uppercase; border: none; margin-bottom: 2px; }
            QLineEdit, QComboBox { 
                background-color: #ffffff; 
                border: 1.5px solid #e2e8f0; 
                border-radius: 10px; 
                padding: 12px 15px; 
                color: #000000; 
                font-size: 14px;
            }
            QLineEdit:focus, QComboBox:focus { border: 2px solid #3b82f6; background-color: #f0f7ff; }
            QComboBox QAbstractItemView { 
                background-color: white; 
                color: #000000; 
                selection-background-color: #3b82f6; 
                selection-color: white; 
                border: 1px solid #e2e8f0;
                outline: none;
            }
        """)
        self.apply_shadow(self.form_card)
        
        grid = QGridLayout(self.form_card)
        grid.setContentsMargins(35, 35, 35, 35)
        grid.setSpacing(18)

        # Helper to add field with label above
        def add_field(label, widget, row, col=0, colspan=1):
            container = QWidget()
            v_lay = QVBoxLayout(container)
            v_lay.setContentsMargins(0, 0, 0, 0)
            v_lay.setSpacing(5)
            v_lay.addWidget(QLabel(label))
            v_lay.addWidget(widget)
            grid.addWidget(container, row, col, 1, colspan)

        # Barcode with Scan Button
        barcode_container = QWidget()
        bc_v_lay = QVBoxLayout(barcode_container)
        bc_v_lay.setContentsMargins(0, 0, 0, 0)
        bc_v_lay.setSpacing(5)
        bc_v_lay.addWidget(QLabel("KODE BARCODE"))
        
        bc_h_lay = QHBoxLayout()
        self.input_barcode = QLineEdit()
        self.input_barcode.setPlaceholderText("Scan atau ketik barcode...")
        self.btn_scan = QPushButton("📷 SCAN")
        self.btn_scan.setCursor(Qt.PointingHandCursor)
        self.btn_scan.setStyleSheet("""
            QPushButton { background-color: #3b82f6; color: white; padding: 12px 20px; font-weight: bold; border-radius: 10px; border: none; }
            QPushButton:hover { background-color: #2563eb; }
        """)
        self.btn_scan.clicked.connect(self.scan_barcode)
        bc_h_lay.addWidget(self.input_barcode)
        bc_h_lay.addWidget(self.btn_scan)
        bc_v_lay.addLayout(bc_h_lay)
        grid.addWidget(barcode_container, 0, 0, 1, 2)

        self.input_nama = QLineEdit(); self.input_nama.setPlaceholderText("Masukkan nama barang...")
        self.input_nama.textChanged.connect(self.auto_fill_rak)
        add_field("NAMA BARANG", self.input_nama, 1, 0, 2)

        self.input_rak = QLineEdit(); self.input_rak.setPlaceholderText("Otomatis Terisi")
        self.input_rak.setReadOnly(True)
        self.input_rak.setStyleSheet("background-color: #f1f5f9; color: #64748b; font-weight: bold; border: 1px dashed #cbd5e1;")
        add_field("NAMA RAK", self.input_rak, 2, 0)

        self.input_satuan = QLineEdit(); self.input_satuan.setPlaceholderText("Contoh: Pcs, Box")
        add_field("SATUAN", self.input_satuan, 2, 1)

        self.combo_kategori = QComboBox()
        add_field("KATEGORI", self.combo_kategori, 3, 0)

        self.combo_lokasi = QComboBox()
        add_field("LOKASI PENYIMPANAN", self.combo_lokasi, 3, 1)
        self.input_stok_min = QLineEdit(); self.input_stok_min.setPlaceholderText("Batas notifikasi...")
        add_field("STOK MINIMUM", self.input_stok_min, 4, 0, 2)

        wrapper_layout.addWidget(self.form_card)

        # --- BUTTON AREA ---
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(15)

        self.btn_simpan = QPushButton("💾 SIMPAN DATA")
        self.btn_simpan.setCursor(Qt.PointingHandCursor)
        self.btn_simpan.setStyleSheet("""
            QPushButton { background-color: #10b981; color: white; font-weight: 900; font-size: 15px; padding: 18px; border-radius: 12px; border: none; }
            QPushButton:hover { background-color: #059669; }
        """)
        self.btn_simpan.clicked.connect(self.simpan_barang)
        
        self.btn_reset = QPushButton("🧹 RESET")
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.setStyleSheet("""
            QPushButton { background-color: #f1f5f9; color: #475569; padding: 18px; border-radius: 12px; border: 1px solid #e2e8f0; font-weight: bold; }
            QPushButton:hover { background-color: #e2e8f0; color: #1e293b; }
        """)
        self.btn_reset.clicked.connect(self.clear_form)
        
        btn_layout.addWidget(self.btn_simpan, 4)
        btn_layout.addWidget(self.btn_reset, 1)
        wrapper_layout.addWidget(btn_container)
        wrapper_layout.addStretch()
        
        content_layout.addWidget(self.wrapper)

        # Final Scroll Area Wrapper
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #f8fafc; }")
        scroll.setWidget(content_area)
        main_layout.addWidget(scroll)

    def apply_shadow(self, widget):
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(20); shadow.setXOffset(0); shadow.setYOffset(4); shadow.setColor(QColor(0, 0, 0, 20))
        widget.setGraphicsEffect(shadow)

    def load_kategori(self):
        self.combo_kategori.clear()
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("SELECT id_kategori, nama_kategori FROM kategori ORDER BY nama_kategori")
            rows = cursor.fetchall()
            for r in rows: self.combo_kategori.addItem(r[1], r[0])
            conn.close()
        except Exception as e: print(f"Load Kategori Error: {e}")

    def load_lokasi(self):
        self.combo_lokasi.clear()
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("SELECT id_lokasi, nama_lokasi FROM lokasi ORDER BY nama_lokasi")
            rows = cursor.fetchall()
            for r in rows: self.combo_lokasi.addItem(r[1], r[0])
            conn.close()
        except Exception as e: print(f"Load Lokasi Error: {e}")

    def set_edit_mode(self, id_b, data):
        """Siapkan form untuk mode edit."""
        self.id_barang_aktif = id_b
        self.title_label.setText(f"✏️ EDIT BARANG: {data['nama']}")
        self.input_barcode.setText(data['barcode'])
        self.input_nama.setText(data['nama'])
        self.input_rak.setText(data['rak'])
        self.input_satuan.setText(data['satuan'])
        self.input_stok_min.setText(str(data['stok_min']))
        
        idx_k = self.combo_kategori.findText(data['kategori'])
        if idx_k >= 0: self.combo_kategori.setCurrentIndex(idx_k)
        
        idx_l = self.combo_lokasi.findText(data['lokasi'])
        if idx_l >= 0: self.combo_lokasi.setCurrentIndex(idx_l)

    def set_add_mode(self):
        self.id_barang_aktif = None
        self.title_label.setText("➕ TAMBAH BARANG BARU")
        self.clear_form()

    def clear_form(self):
        self.input_barcode.clear()
        self.input_nama.clear()
        self.input_rak.clear()
        self.input_satuan.clear()
        self.input_stok_min.clear()
        self.id_barang_aktif = None

    def scan_barcode(self):
        cap = cv2.VideoCapture(0)
        barcode_data = None
        while True:
            ret, frame = cap.read()
            if not ret: break
            for obj in pyzbar.decode(frame):
                barcode_data = obj.data.decode('utf-8'); break
            cv2.imshow("PTPN IV SCANNER (ESC: Keluar)", frame)
            if barcode_data or cv2.waitKey(1) & 0xFF == 27: break
        cap.release(); cv2.destroyAllWindows()
        if barcode_data:
            winsound.Beep(1000, 200)
            self.input_barcode.setText(barcode_data)

    def show_notif(self, title, message, is_error=False):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(QMessageBox.Critical if is_error else QMessageBox.Information)
        msg.setStyleSheet("QMessageBox { background-color: white; } QLabel { color: black; font-size: 13px; font-weight: 500; } QPushButton { color: black; font-weight: bold; min-width: 70px; }")
        msg.exec()

    def auto_fill_rak(self, text):
        if self.id_barang_aktif is None:  # Hanya auto-fill saat mode tambah baru
            if text.strip():
                # Format: "RAK SATU DUA" (Tanpa tanda strip, huruf kapital semua)
                nama_bersih = text.strip().upper()
                self.input_rak.setText(f"RAK {nama_bersih}")
            else:
                self.input_rak.clear()
    def simpan_barang(self):
        nama = self.input_nama.text().strip()
        barcode = self.input_barcode.text().strip()
        rak = self.input_rak.text().strip().upper()
        satuan = self.input_satuan.text().strip()
        stok_min = self.input_stok_min.text().strip() or "0"
        id_kat = self.combo_kategori.currentData()
        id_lok = self.combo_lokasi.currentData()

        # AUTO GENERATE BARCODE JIKA KOSONG
        if not barcode:
            try:
                conn = get_connection(); cursor = conn.cursor()
                cursor.execute("SELECT MAX(id_barang) FROM barang_baru")
                res = cursor.fetchone()[0] or 0
                conn.close()
                barcode = f"BRG{(res + 1):05d}"
                self.input_barcode.setText(barcode)
            except Exception as e:
                print(f"Error auto-generate barcode: {e}")
                self.show_notif("Error", "Gagal auto-generate barcode otomatis.", is_error=True)
                return

        if not nama or not barcode:
            self.show_notif("Peringatan", "Nama dan Barcode wajib diisi!", is_error=True)
            return

        try:
            conn = get_connection(); cursor = conn.cursor()
            if self.id_barang_aktif:
                cursor.execute("""
                    UPDATE barang_baru SET barcode=?, nama_barang=?, rak=?, id_kategori=?, 
                    id_lokasi=?, satuan=?, stok_minimum=? WHERE id_barang=?
                """, (barcode, nama, rak, id_kat, id_lok, satuan, stok_min, self.id_barang_aktif))
                msg = f"Update Barang: {nama}"
            else:
                cursor.execute("""
                    INSERT INTO barang_baru (barcode, nama_barang, rak, id_kategori, id_lokasi, satuan, stok_minimum, stok)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """, (barcode, nama, rak, id_kat, id_lok, satuan, stok_min))
                msg = f"Tambah Barang: {nama}"
            
            conn.commit(); conn.close()
            catat_log(msg)
            
            # Auto-generate/sync barcode
            import os, sys
            from utils.barcode_utils import generate_barcode_image
            if getattr(sys, 'frozen', False):
                root_dir = os.path.dirname(sys.executable)
            else:
                root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            barcode_dir = os.path.join(root_dir, "barcode")
            generate_barcode_image(barcode, barcode_dir)

            self.show_notif("Berhasil", "Data barang berhasil disimpan!")
            self.barang_saved.emit()
            self.back_requested.emit()
        except Exception as e:
            self.show_notif("Gagal", f"Error Simpan: {e}", is_error=True)
