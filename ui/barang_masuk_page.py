import os
import sys
import cv2
import sqlite3
from pyzbar import pyzbar
import winsound
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QTableWidget, QScrollArea,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QGridLayout, QComboBox, QCompleter
)
from PySide6.QtCore import Qt, QSettings, QStringListModel
from PySide6.QtGui import QColor

from database.connection import catat_log
from models.barang_model import BarangModel
from models.transaksi_model import TransaksiModel
from utils.config_manager import get_ip_camera_url

def get_app_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class BarangMasukPage(QWidget):
    """
    Halaman Pencatatan Barang Masuk.
    Dioptimalkan untuk responsivitas maksimal dan ukuran tombol profesional.
    """
    def __init__(self):
        super().__init__()
        self.id_barang_aktif = None
        self.stok_sekarang = 0
        self.metode_input = "MANUAL"
        
        self.settings = QSettings("PTPN4_Inventaris", "SessionState")
        self.init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self.clear_form()
        self.load_transaksi()
        self.update_suplier_autocomplete()

    def update_suplier_autocomplete(self):
        try:
            supliers = TransaksiModel.get_suplier_list()
            self.suplier_model.setStringList(supliers)
        except Exception as e: print(f"Print Label Error: {e}")

    def init_ui(self):
        # Layout Utama
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

        # Global StyleSheet
        self.setStyleSheet("""
            QWidget { font-family: 'Segoe UI', Arial; font-size: 13px; color: #1e293b; }
            QLabel { color: #475569; font-weight: 700; }
            QLineEdit, QComboBox { 
                background-color: white; border: 1px solid #e2e8f0; 
                border-radius: 8px; padding: 8px; color: #1e293b;
            }
            QLineEdit:focus, QComboBox:focus { border: 2px solid #3b82f6; }
            QTableWidget { background-color: white; border-radius: 12px; border: 1px solid #e2e8f0; gridline-color: #f1f5f9; }
            QHeaderView::section { 
                background-color: #f8fafc; color: #475569; font-weight: bold; 
                border: none; border-bottom: 2px solid #e2e8f0; padding: 10px;
            }
        """)

        # --- SECTION 1: SEARCH & SCAN ---
        top_bar_card = QFrame()
        top_bar_card.setStyleSheet("background-color: white; border-radius: 16px; border: 1px solid #e2e8f0;")
        self.apply_shadow(top_bar_card)
        top_bar_layout = QHBoxLayout(top_bar_card)
        top_bar_layout.setContentsMargins(15, 15, 15, 15)
        
        self.input_barcode = QLineEdit()
        self.input_barcode.setPlaceholderText("🔍 Scan atau Ketik Kode Barang...")
        self.input_barcode.setFixedHeight(40) # Ukuran Profesional
        self.input_barcode.returnPressed.connect(self.cari_barang_manual)

        self.btn_cari = QPushButton("CARI DATA")
        self.btn_cari.setCursor(Qt.PointingHandCursor)
        self.btn_cari.setFixedSize(110, 40)
        self.btn_cari.setStyleSheet("background-color: #1e293b; color: white; font-weight: bold;")
        self.btn_cari.clicked.connect(self.cari_barang_manual)
        
        self.btn_scan_kamera = QPushButton("📷 SCAN")
        self.btn_scan_kamera.setCursor(Qt.PointingHandCursor)
        self.btn_scan_kamera.setFixedSize(120, 40)
        self.btn_scan_kamera.setStyleSheet("background-color: #3b82f6; color: white; font-weight: bold;")
        self.btn_scan_kamera.clicked.connect(self.scan_kamera)

        top_bar_layout.addWidget(self.input_barcode, 1)
        top_bar_layout.addWidget(self.btn_cari)
        top_bar_layout.addWidget(self.btn_scan_kamera)
        layout.addWidget(top_bar_card)

        # --- SECTION 2: DETAIL INFORMASI BARANG ---
        detail_card = QFrame()
        detail_card.setStyleSheet("background-color: white; border-radius: 16px; border: 1px solid #e2e8f0;")
        self.apply_shadow(detail_card)
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(20, 20, 20, 20)

        detail_title = QLabel("DETAIL VALIDASI BARANG")
        detail_title.setStyleSheet("font-size: 13px; color: #1e293b; margin-bottom: 5px; text-transform: uppercase;")
        detail_layout.addWidget(detail_title)

        info_grid = QGridLayout()
        info_grid.setSpacing(12)
        
        label_s = "color: #64748b; font-size: 11px; text-transform: uppercase; font-weight: 800;"
        val_s = "background-color: #f8fafc; font-weight: 600; color: #1e293b; border: 1px solid #f1f5f9; padding: 10px;"

        info_grid.addWidget(QLabel("NAMA BARANG", styleSheet=label_s), 0, 0)
        self.nama_barang = QLineEdit(); self.nama_barang.setReadOnly(True); self.nama_barang.setStyleSheet(val_s)
        info_grid.addWidget(self.nama_barang, 1, 0)

        info_grid.addWidget(QLabel("KATEGORI", styleSheet=label_s), 0, 1)
        self.kat_detail = QLineEdit(); self.kat_detail.setReadOnly(True); self.kat_detail.setStyleSheet(val_s)
        info_grid.addWidget(self.kat_detail, 1, 1)

        info_grid.addWidget(QLabel("RAK PENYIMPANAN", styleSheet=label_s), 2, 0)
        self.rak_detail = QLineEdit(); self.rak_detail.setReadOnly(True); self.rak_detail.setStyleSheet(val_s)
        info_grid.addWidget(self.rak_detail, 3, 0)

        info_grid.addWidget(QLabel("PILIH SLOT LOKASI", styleSheet=label_s), 2, 1)
        self.slot_combo = QComboBox()
        self.slot_combo.setFixedHeight(38)
        self.slot_combo.currentIndexChanged.connect(self.update_info_slot_pilihan)
        info_grid.addWidget(self.slot_combo, 3, 1)

        # Stok Display (Dikecilkan biar gak jumbo)
        info_grid.addWidget(QLabel("STOK SAAT INI", styleSheet=label_s), 0, 2)
        self.stok_display = QLineEdit(); self.stok_display.setReadOnly(True)
        self.stok_display.setFixedSize(110, 85)
        self.stok_display.setAlignment(Qt.AlignCenter)
        self.stok_display.setStyleSheet("""
            background-color: #f0f9ff; border: 2px solid #bae6fd; 
            border-radius: 12px; color: #0369a1; font-size: 28px; font-weight: 800;
        """)
        info_grid.addWidget(self.stok_display, 1, 2, 3, 1)

        detail_layout.addLayout(info_grid)
        detail_layout.addSpacing(10)

        # Qty Input & Simpan (Lebih Ramping)
        action_layout = QHBoxLayout()
        
        v_ket = QVBoxLayout()
        v_ket.addWidget(QLabel("SUPLIER", styleSheet=label_s))
        self.keterangan_input = QLineEdit()
        self.keterangan_input.setPlaceholderText("Wajib: Nama Suplier")
        self.keterangan_input.setFixedHeight(50)
        self.keterangan_input.setStyleSheet("font-size: 14px; background-color: #f8fafc;")
        
        self.suplier_model = QStringListModel()
        self.suplier_completer = QCompleter(self.suplier_model, self)
        self.suplier_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.suplier_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.keterangan_input.setCompleter(self.suplier_completer)
        
        v_ket.addWidget(self.keterangan_input)
        action_layout.addLayout(v_ket, 2)

        v_qty = QVBoxLayout()
        v_qty.addWidget(QLabel("JUMLAH MASUK", styleSheet=label_s))
        self.jumlah = QLineEdit(); self.jumlah.setText("0")
        self.jumlah.setFixedHeight(50)
        self.jumlah.setAlignment(Qt.AlignCenter)
        self.jumlah.setStyleSheet("""
            font-size: 24px; font-weight: 800; border: 2px solid #10b981; 
            color: #047857; background: #ecfdf5; border-radius: 8px;
        """)
        v_qty.addWidget(self.jumlah); action_layout.addLayout(v_qty, 1)

        self.btn_simpan = QPushButton("✅ SIMPAN TRANSAKSI")
        self.btn_simpan.setFixedHeight(70); self.btn_simpan.setCursor(Qt.PointingHandCursor)
        self.btn_simpan.setStyleSheet("""
            QPushButton { background-color: #10b981; color: white; font-size: 14px; font-weight: 800; border-radius: 8px; margin-top: 5px; }
            QPushButton:hover { background-color: #059669; }
        """)
        self.btn_simpan.clicked.connect(self.simpan_transaksi)
        action_layout.addWidget(self.btn_simpan, 2)
        
        detail_layout.addLayout(action_layout)
        layout.addWidget(detail_card)

        # --- SECTION 3: TABLE RIWAYAT ---
        history_header = QHBoxLayout()
        history_header.addWidget(QLabel("📋 RIWAYAT TRANSAKSI SESI INI", styleSheet="font-size: 13px; font-weight: 800; color: #1e293b;"))
        history_header.addStretch()
        self.btn_cls = QPushButton("🧹 BERSIHKAN")
        self.btn_cls.setCursor(Qt.PointingHandCursor)
        self.btn_cls.setStyleSheet("background-color: #94a3b8; color: white; padding: 6px 12px; font-size: 11px; border-radius: 6px;")
        self.btn_cls.clicked.connect(self.bersihkan_tampilan_tabel)
        history_header.addWidget(self.btn_cls)
        layout.addLayout(history_header)

        self.table = QTableWidget()
        self.table.setMinimumHeight(250)
        self.table.setColumnCount(10) 
        self.table.setHorizontalHeaderLabels(["WAKTU", "KODE", "BARANG", "RAK", "SLOT", "QTY", "AWAL", "AKHIR", "METODE", "SUPLIER"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget { background-color: white; border-radius: 16px; border: 1px solid #e2e8f0; gridline-color: #f1f5f9; }
            QHeaderView::section { background: #f8fafc; color: #475569; font-weight: bold; border: none; border-bottom: 2px solid #e2e8f0; padding: 12px; }
            QTableWidget::item { padding: 5px; }
            QTableWidget::item:selected { background-color: #eff6ff; color: #1e293b; }
        """)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.itemClicked.connect(self.print_label_dari_tabel)
        self.apply_shadow(self.table)
        layout.addWidget(self.table)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def apply_shadow(self, widget):
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(20); shadow.setXOffset(0); shadow.setYOffset(4); shadow.setColor(QColor(0, 0, 0, 20))
        widget.setGraphicsEffect(shadow)

    # ========================================================
    # LOGIC FUNCTIONS
    # ========================================================
    def show_notif(self, title, text, is_error=False):
        msg = QMessageBox(self)
        msg.setWindowTitle(title); msg.setText(text)
        msg.setIcon(QMessageBox.Critical if is_error else QMessageBox.Information)
        msg.setStyleSheet("""
            QMessageBox { background-color: white; } 
            QLabel { color: black; font-size: 13px; font-weight: normal; } 
            QPushButton { color: black; font-weight: bold; background-color: #f1f5f9; border: 1px solid #cbd5e1; min-width: 70px; padding: 5px; }
        """)
        msg.exec()

    def bersihkan_tampilan_tabel(self):
        self.settings.setValue("checkpoint_masuk", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        self.table.setRowCount(0); self.show_notif("Info", "Tampilan riwayat sesi ini telah dibersihkan.")

    def load_transaksi(self):
        try:
            checkpoint = self.settings.value("checkpoint_masuk", "2000-01-01 00:00:00")
            rows = TransaksiModel.get_history_paged('MASUK', checkpoint)
            self.table.setRowCount(0)
            for i, row in enumerate(rows):
                self.table.insertRow(i)
                data = [str(row["tanggal"]), str(row["barcode"]), str(row["nama_barang"]), str(row["rak"]), str(row["slot"]), f"+{row['qty']}", str(row["stok_sebelum"]), str(row["stok_sesudah"]), str(row["metode"]), str(row["keterangan"] or "-")]
                for col, text in enumerate(data):
                    ti = QTableWidgetItem(text)
                    if col in [0, 5, 6, 7]: ti.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(i, col, ti)
        except Exception as e: print(f"Load Riwayat Error: {e}")

    def cari_barang_manual(self):
        barcode = self.input_barcode.text().strip()
        self.metode_input = "MANUAL"
        if self.cari_barang_logic(barcode):
            self.jumlah.setFocus(); self.jumlah.selectAll()

    def cari_barang_logic(self, barcode_val):
        if not barcode_val: return False
        try:
            rows = BarangModel.get_by_barcode(barcode_val)
            if rows:
                self.nama_barang.setText(rows[0]["nama_barang"])
                self.kat_detail.setText(rows[0]["nama_kategori"] if rows[0]["nama_kategori"] else "-")
                self.slot_combo.clear()
                for row in rows:
                    self.slot_combo.addItem(row["nama_slot"], {"id": row["id_barang"], "stok": row["stok"], "rak": row["rak"]})
                return True
            self.show_notif("Gagal", "Barang tidak ditemukan!", is_error=True); return False
        except Exception as e:
            self.show_notif("Error", f"Terjadi kesalahan saat mencari data: {e}", is_error=True)
            return False

    def update_info_slot_pilihan(self):
        data = self.slot_combo.currentData()
        if data:
            self.id_barang_aktif, self.stok_sekarang = data["id"], data["stok"]
            self.rak_detail.setText(data["rak"] if data["rak"] else "-")
            self.stok_display.setText(str(data["stok"]))

    def scan_kamera(self):
        cam_url = get_ip_camera_url()
        cap = None
        
        if cam_url:
            cap = cv2.VideoCapture(cam_url)
            ret, _ = cap.read()
            if not ret:
                cap.release()
                cap = None
        
        if cap is None:
            cap = cv2.VideoCapture(0)
            
        if not cap.isOpened():
            self.show_notif("Gagal", "Tidak dapat membuka kamera (IP maupun Lokal).", is_error=True)
            return
            
        barcode_data = None
        while True:
            ret, frame = cap.read()
            if not ret: break
            
            frame = cv2.resize(frame, (640, 480))
            for obj in pyzbar.decode(frame):
                barcode_data = obj.data.decode('utf-8'); break
            
            cv2.imshow("SCANNER MASUK (ESC: Keluar)", frame)
            
            if barcode_data:
                winsound.Beep(1000, 150)
                self.metode_input = "SCAN"
                
                # AUTO SINKRON & AKUMULASI KOMULATIF
                if self.input_barcode.text() == barcode_data and self.id_barang_aktif:
                    try:
                        current_qty = int(self.jumlah.text() or 0)
                        self.jumlah.setText(str(current_qty + 1))
                    except: self.jumlah.setText("1")
                else:
                    self.input_barcode.setText(barcode_data)
                    if self.cari_barang_logic(barcode_data):
                        self.jumlah.setText("1")
                break
                
            if cv2.waitKey(1) & 0xFF == 27: break 
        cap.release(); cv2.destroyAllWindows()

    def simpan_transaksi(self):
        try:
            qty_text = self.jumlah.text()
            qty = int(qty_text) if qty_text.isdigit() else 0
            if qty <= 0: self.show_notif("Peringatan", "Jumlah harus lebih dari 0", is_error=True); return
            if not self.id_barang_aktif: self.show_notif("Peringatan", "Cari barang dulu!", is_error=True); return
            
            ket = self.keterangan_input.text().strip()
            if not ket: self.show_notif("Peringatan", "Nama Suplier Wajib Diisi!", is_error=True); return
            
            st_akhir = self.stok_sekarang + qty
            w_skrg = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if BarangModel.update_stok(self.id_barang_aktif, st_akhir):
                TransaksiModel.record_transaksi(self.id_barang_aktif, 'MASUK', self.stok_sekarang, st_akhir, self.metode_input, w_skrg, ket, sisa_qty=qty)
                catat_log(f"Barang Masuk: {ket} mengirim +{qty} {self.nama_barang.text()}")
            else:
                 self.show_notif("Gagal", "Database error.", is_error=True); return
            
            self.generate_label_teks(self.nama_barang.text(), w_skrg, self.input_barcode.text())
            self.show_notif("Berhasil", f"Stok ditambah sebanyak {qty}.")
            self.clear_form(); self.load_transaksi()
        except Exception as e: self.show_notif("Error", f"Gagal: {e}", is_error=True)

    def clear_form(self):
        self.id_barang_aktif = None; self.stok_sekarang = 0
        self.input_barcode.clear(); self.nama_barang.clear(); self.kat_detail.clear()
        self.rak_detail.clear(); self.slot_combo.clear(); self.stok_display.clear(); self.keterangan_input.clear(); self.jumlah.setText("0"); self.input_barcode.setFocus()

    def generate_label_teks(self, nama, waktu, barcode):
        try:
            folder = os.path.join(get_app_path(), "label_masuk")
            if not os.path.exists(folder): os.makedirs(folder)
            w_obj = datetime.strptime(waktu, '%Y-%m-%d %H:%M:%S')
            img = Image.new('RGB', (400, 220), color='white'); d = ImageDraw.Draw(img)
            d.text((20, 20), "PTPN IV - FIFO LABEL", fill=(0,0,0))
            d.text((20, 60), f"BARANG: {nama[:25]}", fill=(0,0,0))
            d.text((20, 90), f"KODE  : {barcode}", fill=(0,0,0))
            d.text((20, 120), f"RAK   : {self.rak_detail.text()}", fill=(0,0,0))
            d.text((20, 150), f"SLOT  : {self.slot_combo.currentText()}", fill=(0,0,0))
            d.text((20, 180), f"TGL   : {w_obj.strftime('%d/%m/%Y %H:%M')}", fill=(0,0,0))
            img.save(os.path.join(folder, f"LABEL_{w_obj.strftime('%d%m%Y%H%M')}_{barcode}.png"))
        except Exception as e: print(f"Generate Label Error: {e}")

    def print_label_dari_tabel(self, item):
        row = item.row(); waktu_raw, barcode_id = self.table.item(row, 0).text(), self.table.item(row, 1).text()
        try:
            dt = datetime.strptime(waktu_raw, '%Y-%m-%d %H:%M:%S')
            path = os.path.abspath(os.path.join(get_app_path(), "label_masuk", f"LABEL_{dt.strftime('%d%m%Y%H%M')}_{barcode_id}.png"))
            if os.path.exists(path):
                msg = QMessageBox(self)
                msg.setWindowTitle("Cetak Label")
                msg.setText("Cetak label FIFO untuk transaksi ini?")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.setStyleSheet("QMessageBox{background:white;} QLabel{color:black;} QPushButton{color:black; min-width:60px;}")
                if msg.exec() == QMessageBox.Yes:
                    if os.name == 'nt': os.startfile(path, "print")
                    else: subprocess.run(['lpr', path])
        except Exception as e: print(f"Print Label Error: {e}")
