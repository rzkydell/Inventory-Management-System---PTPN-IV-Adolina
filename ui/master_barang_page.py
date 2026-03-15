import os
import sqlite3
import cv2
import winsound
import subprocess
import sys
from pyzbar import pyzbar
from barcode import Code128
from barcode.writer import ImageWriter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QFileDialog,
    QTableWidgetItem, QComboBox, QMessageBox, QInputDialog,
    QHeaderView, QAbstractItemView, QFrame, QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from database.connection import get_connection, catat_log
from datetime import datetime

from utils.path_helper import get_resource_path, get_root_dir
from utils.config_manager import get_ip_camera_url

class MasterBarangPage(QWidget):
    """
    Halaman Master Barang (List View).
    """
    add_requested = Signal()
    edit_requested = Signal(int, dict) # id_barang, data_dict
    def __init__(self):
        super().__init__()
        self.id_barang_aktif = None 
        self.font_path = get_resource_path("assets/font/Apple.ttf")
        
        self.barcode_dir = os.path.join(get_root_dir(), "barcode")
        if not os.path.exists(self.barcode_dir):
            os.makedirs(self.barcode_dir)

        self.init_ui()
        self.load_kategori()
        self.load_barang()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_kategori()
        self.search_barang.clear()
        self.filter_kategori.setCurrentIndex(0)
        self.clear_form()
        self.load_barang()

    def init_ui(self):
        # Layout utama tanpa margin agar ScrollArea menempel ke pinggir
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # --- MANDATORY SCROLL AREA UNTUK LAPTOP LAYAR KECIL ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #f8fafc; }")
        
        container = QWidget()
        container.setStyleSheet("background-color: #f8fafc;")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        self.setStyleSheet("""
            QWidget { font-family: 'Segoe UI', Arial; font-size: 13px; color: #1e293b; }
            QLabel { color: #000000; font-weight: 700; }
            QLineEdit, QComboBox { 
                background-color: white; border: 1px solid #e2e8f0; 
                border-radius: 8px; padding: 8px; color: #000000;
            }
            QLineEdit:focus, QComboBox:focus { border: 2px solid #3b82f6; }
            QComboBox QAbstractItemView { 
                background-color: white; color: #000000; 
                selection-background-color: #3b82f6; selection-color: white; 
                outline: none;
            }
        """)

        # --- SECTION 1: SEARCH & ACTIONS ---
        header_card = QFrame()
        header_card.setStyleSheet("background-color: #f1f5f9; border-radius: 16px; border: 1px solid #e2e8f0;")
        self.apply_shadow(header_card)
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(20, 15, 20, 15)
        header_layout.setSpacing(12)

        # Row 1: Search & Filter
        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        
        self.search_barang = QLineEdit()
        self.search_barang.setPlaceholderText("🔍 Cari Nama, Kode, atau RAK...")
        self.search_barang.setMinimumHeight(40)
        
        self.btn_scan_search = QPushButton("📷 SCAN")
        self.btn_scan_search.setCursor(Qt.PointingHandCursor)
        self.btn_scan_search.setFixedWidth(100)
        self.btn_scan_search.setStyleSheet("""
            QPushButton { background-color: #3b82f6; color: white; font-weight: bold; height: 40px; border-radius: 8px; }
            QPushButton:hover { background-color: #2563eb; }
        """)
        self.btn_scan_search.clicked.connect(lambda: self.scan_kamera(target="search"))
        
        self.filter_kategori = QComboBox()
        self.filter_kategori.setMinimumWidth(200)
        self.filter_kategori.setMinimumHeight(40)
        self.filter_kategori.currentIndexChanged.connect(self.filter_barang)

        search_row.addWidget(QLabel("CARI:"), 0)
        search_row.addWidget(self.search_barang, 2)
        search_row.addWidget(self.btn_scan_search, 0)
        search_row.addSpacing(15)
        search_row.addWidget(QLabel("KATEGORI:"), 0)
        search_row.addWidget(self.filter_kategori, 1)
        header_layout.addLayout(search_row)

        # Row 2: Main Buttons
        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        # Button Style Helper
        btn_style = "QPushButton { color: white; font-weight: bold; height: 42px; border-radius: 10px; }"
        
        self.btn_tambah_ui = QPushButton("➕ TAMBAH BARANG")
        self.btn_tambah_ui.setCursor(Qt.PointingHandCursor)
        self.btn_tambah_ui.setFixedWidth(160)
        self.btn_tambah_ui.setStyleSheet(btn_style + " QPushButton { background-color: #3b82f6; } QPushButton:hover { background-color: #2563eb; }")
        self.btn_tambah_ui.clicked.connect(lambda: self.add_requested.emit())

        self.btn_edit_ui = QPushButton("📝 EDIT")
        self.btn_edit_ui.setCursor(Qt.PointingHandCursor)
        self.btn_edit_ui.setFixedWidth(100)
        self.btn_edit_ui.setStyleSheet(btn_style + " QPushButton { background-color: #10b981; } QPushButton:hover { background-color: #059669; }")
        self.btn_edit_ui.clicked.connect(self.trigger_edit_signal)

        self.btn_hapus_ui = QPushButton("🗑️ HAPUS")
        self.btn_hapus_ui.setCursor(Qt.PointingHandCursor)
        self.btn_hapus_ui.setFixedWidth(100)
        self.btn_hapus_ui.setStyleSheet(btn_style + " QPushButton { background-color: #ef4444; } QPushButton:hover { background-color: #dc2626; }")
        self.btn_hapus_ui.clicked.connect(self.hapus_barang)

        self.btn_import_csv = QPushButton("📥 IMPORT CSV")
        self.btn_import_csv.setCursor(Qt.PointingHandCursor)
        self.btn_import_csv.setFixedWidth(140)
        self.btn_import_csv.setStyleSheet(btn_style + " QPushButton { background-color: #6366f1; } QPushButton:hover { background-color: #4f46e5; }")
        self.btn_import_csv.clicked.connect(self.import_csv_massal)

        action_row.addWidget(self.btn_tambah_ui)
        action_row.addWidget(self.btn_edit_ui)
        action_row.addWidget(self.btn_hapus_ui)
        action_row.addStretch()
        action_row.addWidget(self.btn_import_csv)
        header_layout.addLayout(action_row)
        
        main_layout.addWidget(header_card)

        # --- SECTION 2: TABLE (AUTO STRETCH) ---
        # Kita berikan minimum height agar tabel tetap terlihat proporsional
        self.table = QTableWidget()
        self.table.setMinimumHeight(250)
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(["√", "No", "Kode Barang", "Nama Barang", "RAK", "Kategori", "Lokasi", "Satuan", "Stok Min", "Stok"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch) # Nama Barang stretch
        self.table.setColumnWidth(0, 30) # Checkbox col
        self.table.setColumnWidth(1, 40) # No col

        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget { background: white; border-top: 1px solid #e2e8f0; gridline-color: #f1f5f9; outline: none; }
            QHeaderView::section { background: #f8fafc; color: #000000; font-weight: 800; font-size: 11px; text-transform: uppercase; border: none; border-bottom: 2px solid #e2e8f0; padding: 12px; }
            QTableWidget::item { padding: 10px; color: #000000; border-bottom: 1px solid #f1f5f9; }
            QTableWidget::item:selected { background-color: #eff6ff; color: #000000; }
        """)
        self.apply_shadow(self.table)
        self.table.itemClicked.connect(self.update_active_id)
        self.table.itemDoubleClicked.connect(self.trigger_edit_signal)
        main_layout.addWidget(self.table, 1)

        # --- SMART BULK ACTIONS BAR ---
        self.bulk_bar = QFrame()
        self.bulk_bar.setStyleSheet("background-color: #f1f5f9; border-radius: 12px; border: 1px solid #e2e8f0;")
        self.apply_shadow(self.bulk_bar)
        bulk_layout = QHBoxLayout(self.bulk_bar)
        bulk_layout.setContentsMargins(15, 8, 15, 8)
        
        lbl_bulk = QLabel("⚡ AKSI MASSAL (Centang Tabel):")
        lbl_bulk.setStyleSheet("font-size: 11px; color: #475569; font-weight: 800;")
        bulk_layout.addWidget(lbl_bulk)
        
        self.btn_bulk_kat = QPushButton("🏷️ UBAH KATEGORI")
        self.btn_bulk_kat.setStyleSheet("background-color: #6366f1; color: white; font-weight: bold; padding: 6px 12px; border-radius: 6px; font-size: 10px;")
        self.btn_bulk_kat.clicked.connect(self.bulk_update_kategori)
        
        self.btn_bulk_loc = QPushButton("📍 UBAH LOKASI")
        self.btn_bulk_loc.setStyleSheet("background-color: #8b5cf6; color: white; font-weight: bold; padding: 8px 15px; border-radius: 8px; font-size: 11px;")
        self.btn_bulk_loc.clicked.connect(self.bulk_update_lokasi)
        
        self.btn_cetak_semua = QPushButton("🖨️ CETAK SEMUA BARCODE (PDF)")
        self.btn_cetak_semua.setCursor(Qt.PointingHandCursor)
        self.btn_cetak_semua.setStyleSheet("background-color: #f59e0b; color: white; font-weight: bold; padding: 8px 15px; border-radius: 8px; font-size: 11px;")
        self.btn_cetak_semua.clicked.connect(self.cetak_semua_barcode)

        self.btn_cetak_terpilih = QPushButton("🖨️ CETAK TERPILIH")
        self.btn_cetak_terpilih.setCursor(Qt.PointingHandCursor)
        self.btn_cetak_terpilih.setStyleSheet("background-color: #ec4899; color: white; font-weight: bold; padding: 8px 15px; border-radius: 8px; font-size: 11px;")
        self.btn_cetak_terpilih.clicked.connect(self.cetak_barcode_terpilih_massal)
        
        bulk_layout.addWidget(self.btn_bulk_kat)
        bulk_layout.addWidget(self.btn_bulk_loc)
        bulk_layout.addStretch()
        bulk_layout.addWidget(self.btn_cetak_terpilih)
        bulk_layout.addWidget(self.btn_cetak_semua)
        
        main_layout.addWidget(self.bulk_bar)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def update_active_id(self, item):
        row = item.row()
        self.id_barang_aktif = self.table.item(row, 1).data(Qt.UserRole)

    def trigger_edit_signal(self, item=None):
        if item:
            row = item.row()
        else:
            row = self.table.currentRow()
            if row < 0:
                self.show_notif("Peringatan", "Pilih barang yang ingin diedit.", is_error=True); return
        
        id_b = self.table.item(row, 1).data(Qt.UserRole)
        data = {
            "barcode": self.table.item(row, 2).text(),
            "nama": self.table.item(row, 3).text(),
            "rak": self.table.item(row, 4).text(),
            "kategori": self.table.item(row, 5).text(),
            "lokasi": self.table.item(row, 6).text(),
            "satuan": self.table.item(row, 7).text(),
            "stok_min": self.table.item(row, 8).text()
        }
        self.edit_requested.emit(id_b, data)

    def clear_form(self):
        self.id_barang_aktif = None
        self.table.clearSelection()

    def apply_shadow(self, widget):
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(20); shadow.setXOffset(0); shadow.setYOffset(4); shadow.setColor(QColor(0, 0, 0, 20))
        widget.setGraphicsEffect(shadow)

    def show_notif(self, title, message, is_error=False):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(QMessageBox.Critical if is_error else QMessageBox.Information)
        msg.setStyleSheet("QMessageBox { background-color: white; } QLabel { color: black; font-size: 13px; font-weight: 500; } QPushButton { color: black; font-weight: bold; min-width: 70px; }")
        msg.exec()

    def scan_kamera(self, target="search"):
        cam_url = get_ip_camera_url()
        cam_source = cam_url if cam_url else 0
        
        cap = cv2.VideoCapture(cam_source)
        if not cap.isOpened():
            self.show_notif("Gagal", f"Tidak dapat membuka kamera ({'IP Webcam' if cam_url else 'Webcam'}).", is_error=True)
            return
            
        barcode_data = None
        while True:
            ret, frame = cap.read()
            if not ret: break
            
            # RESIZE FRAME (UX Improvement: Jendela tidak memenuhi layar)
            frame = cv2.resize(frame, (640, 480))
            
            for obj in pyzbar.decode(frame):
                barcode_data = obj.data.decode('utf-8')
                break
                
            cv2.imshow("PTPN IV SCANNER (ESC: Keluar)", frame)
            
            if barcode_data or cv2.waitKey(1) & 0xFF == 27:
                break
                
        cap.release()
        cv2.destroyAllWindows()
        
        if barcode_data:
            winsound.Beep(1000, 200)
            if target == "search":
                self.search_barang.setText(barcode_data)
                self.filter_barang()
            self.show_notif("Berhasil", f"Barcode terdeteksi: {barcode_data}")

    def load_barang(self):
        try:
            conn = get_connection(); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
            cursor.execute("""
                SELECT b.*, k.nama_kategori, l.nama_lokasi FROM barang_baru b 
                LEFT JOIN kategori k ON b.id_kategori = k.id_kategori 
                LEFT JOIN lokasi l ON b.id_lokasi = l.id_lokasi ORDER BY b.id_barang ASC
            """)
            rows = cursor.fetchall(); self.table.setRowCount(0)
            for i, row in enumerate(rows):
                self.table.insertRow(i)
                
                # Checkbox (Col 0)
                chk = QTableWidgetItem()
                chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                chk.setCheckState(Qt.Unchecked)
                self.table.setItem(i, 0, chk)
                
                # Data Cols
                item_no = QTableWidgetItem(str(i + 1))
                item_no.setData(Qt.UserRole, row["id_barang"])
                self.table.setItem(i, 1, item_no)
                
                self.table.setItem(i, 2, QTableWidgetItem(str(row["barcode"])))
                self.table.setItem(i, 3, QTableWidgetItem(str(row["nama_barang"])))
                self.table.setItem(i, 4, QTableWidgetItem(str(row["rak"] or "-")))
                self.table.setItem(i, 5, QTableWidgetItem(str(row["nama_kategori"])))
                self.table.setItem(i, 6, QTableWidgetItem(str(row["nama_lokasi"])))
                self.table.setItem(i, 7, QTableWidgetItem(str(row["satuan"] or "-")))
                
                min_stok_item = QTableWidgetItem(str(row["stok_minimum"]))
                self.table.setItem(i, 8, min_stok_item)
                
                stok_item = QTableWidgetItem(str(row["stok"]))
                if row["stok"] <= row["stok_minimum"]:
                    stok_item.setForeground(QColor("#ef4444"))
                    font = QFont(); font.setBold(True); stok_item.setFont(font)
                self.table.setItem(i, 9, stok_item)

                # Alignment
                for c in [1, 2, 4, 8, 9]:
                    if self.table.item(i, c):
                        self.table.item(i, c).setTextAlignment(Qt.AlignCenter)
            conn.close()
        except Exception as e: print(f"Load Error: {e}")

    def get_checked_ids(self):
        ids = []
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0).checkState() == Qt.Checked:
                ids.append(self.table.item(r, 1).data(Qt.UserRole))
        if not ids:
            self.show_notif("Peringatan", "Silakan centang barang di tabel terlebih dahulu.", is_error=True)
        return ids

    def bulk_update_kategori(self):
        ids = self.get_checked_ids()
        if not ids: return
        
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT id_kategori, nama_kategori FROM kategori ORDER BY nama_kategori")
        kats = cursor.fetchall(); conn.close()
        kat_names = [r[1] for r in kats]
        if not kat_names: return
        
        input_dialog = QInputDialog(self)
        input_dialog.setWindowTitle("Edit Massal")
        input_dialog.setLabelText(f"Pilih Kategori Baru untuk {len(ids)} Item:")
        input_dialog.setComboBoxItems(kat_names)
        input_dialog.setStyleSheet("""
            QInputDialog { background-color: white; }
            QLabel { color: black; font-weight: bold; }
            QComboBox { background: white; color: black; border: 1px solid #cbd5e0; border-radius: 6px; padding: 5px; }
            QPushButton { color: white; background: #3b82f6; border-radius: 6px; padding: 5px 15px; font-weight: bold; }
            QPushButton:hover { background: #2563eb; }
        """)
        
        ok = input_dialog.exec()
        item = input_dialog.textValue() if input_dialog.inputMode() == QInputDialog.TextInput else input_dialog.comboBoxValue()

        if ok and item:
            new_id = kats[kat_names.index(item)][0]
            try:
                conn = get_connection(); cursor = conn.cursor()
                for bid in ids:
                    cursor.execute("UPDATE barang_baru SET id_kategori = ? WHERE id_barang = ?", (new_id, bid))
                conn.commit(); conn.close()
                catat_log(f"Bulk Update Kategori: {len(ids)} item diubah ke {item}")
                self.load_barang(); self.show_notif("Sukses", f"{len(ids)} barang berhasil diperbarui.")
            except Exception as e: self.show_notif("Gagal", str(e), is_error=True)

    def bulk_update_lokasi(self):
        ids = self.get_checked_ids()
        if not ids: return
        
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT id_lokasi, nama_lokasi FROM lokasi ORDER BY nama_lokasi")
        locs = cursor.fetchall(); conn.close()
        loc_names = [r[1] for r in locs]
        if not loc_names: return
        
        input_dialog = QInputDialog(self)
        input_dialog.setWindowTitle("Edit Massal")
        input_dialog.setLabelText(f"Pilih Lokasi Baru untuk {len(ids)} Item:")
        input_dialog.setComboBoxItems(loc_names)
        input_dialog.setStyleSheet("""
            QInputDialog { background-color: white; }
            QLabel { color: black; font-weight: bold; }
            QComboBox { background: white; color: black; border: 1px solid #cbd5e0; border-radius: 6px; padding: 5px; }
            QPushButton { color: white; background: #3b82f6; border-radius: 6px; padding: 5px 15px; font-weight: bold; }
            QPushButton:hover { background: #2563eb; }
        """)
        
        ok = input_dialog.exec()
        item = input_dialog.textValue() if input_dialog.inputMode() == QInputDialog.TextInput else input_dialog.comboBoxValue()

        if ok and item:
            new_id = locs[loc_names.index(item)][0]
            try:
                conn = get_connection(); cursor = conn.cursor()
                for bid in ids:
                    cursor.execute("UPDATE barang_baru SET id_lokasi = ? WHERE id_barang = ?", (new_id, bid))
                conn.commit(); conn.close()
                catat_log(f"Bulk Update Lokasi: {len(ids)} item diubah ke {item}")
                self.load_barang(); self.show_notif("Sukses", f"{len(ids)} barang berhasil diperbarui.")
            except Exception as e: self.show_notif("Gagal", str(e), is_error=True)

    def filter_barang(self):
        kw = self.search_barang.text().lower()
        kat = self.filter_kategori.currentText()
        nomor_urut = 1 
        for r in range(self.table.rowCount()):
            kode = self.table.item(r, 2).text().lower()
            nama = self.table.item(r, 3).text().lower()
            rak_t = self.table.item(r, 4).text().lower()
            kat_t = self.table.item(r, 5).text()
            match = (kw in nama or kw in kode or kw in rak_t) and (kat == "Semua Kategori" or kat_t == kat)
            if match:
                self.table.setRowHidden(r, False)
                self.table.item(r, 1).setText(str(nomor_urut))
                nomor_urut += 1
            else: self.table.setRowHidden(r, True)

    def hapus_barang(self):
        row = self.table.currentRow()
        if row < 0:
            self.show_notif("Peringatan", "Pilih barang yang ingin dihapus.", is_error=True); return
            
        id_b = self.table.item(row, 1).data(Qt.UserRole)
        nama = self.table.item(row, 3).text()
        kode = self.table.item(row, 2).text()
        msg = QMessageBox(self)
        msg.setWindowTitle("Konfirmasi Hapus")
        msg.setText(f"Hapus '{nama}'?")
        msg.setInformativeText("Data transaksi terkait mungkin akan terpengaruh.")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setStyleSheet("QMessageBox { background-color: white; } QLabel { color: black; } QPushButton { color: black; min-width: 70px; }")
        if msg.exec() == QMessageBox.Yes:
            try:
                self.remove_barcode_file(kode)
                conn = get_connection(); cursor = conn.cursor()
                cursor.execute("DELETE FROM barang_baru WHERE id_barang=?", (self.id_barang_aktif,))
                conn.commit(); conn.close()

                catat_log(f"Menghapus master barang: {kode} - {nama}")

                self.clear_form(); self.load_barang()
                self.show_notif("Berhasil", f"Data '{nama}' telah dihapus.")
            except: self.show_notif("Error", "Gagal menghapus data.", is_error=True)
            
    def opname_stok(self):
        if not self.id_barang_aktif:
            self.show_notif("Peringatan", "Pilih barang dari tabel terlebih dahulu.", is_error=True); return
        row = self.table.currentRow()
        nama = self.table.item(row, 3).text()
        stok_lama = int(self.table.item(row, 9).text())
        
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Opname Stok Fisik")
        dialog.setLabelText(f"Masukkan stok fisik terbaru untuk:\n{nama}\n\nStok saat ini: {stok_lama}")
        dialog.setStyleSheet("QInputDialog { background-color: white; } QLabel { color: black; font-size: 13px; font-weight: bold; } QLineEdit { background: white; color: black; border: 1px solid #cbd5e0; border-radius: 6px; padding: 5px; } QPushButton { color: white; background: #3b82f6; border-radius: 6px; padding: 5px 15px; font-weight: bold; } QPushButton:hover { background: #2563eb; } QPushButton[text='Cancel'] { background: #ef4444; }")
        
        ok = dialog.exec()
        stok_baru_str = dialog.textValue()
        
        if ok and stok_baru_str.strip():
            try:
                stok_baru = int(stok_baru_str.strip())
                if stok_baru == stok_lama: return
                
                kemana = 'MASUK' if stok_baru > stok_lama else 'KELUAR'
                conn = get_connection(); cursor = conn.cursor()
                try:
                    w_skrg = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute("UPDATE barang_baru SET stok = ? WHERE id_barang = ?", (stok_baru, self.id_barang_aktif))
                    cursor.execute("""
                        INSERT INTO transaksi (id_barang, jenis, stok_sebelum, stok_sesudah, metode, tanggal, keterangan) 
                        VALUES (?, ?, ?, ?, 'MANUAL', ?, ?)
                    """, (self.id_barang_aktif, kemana, stok_lama, stok_baru, w_skrg, "REVISI OPNAME STOK"))
                    conn.commit()
                except Exception as e:
                    conn.rollback(); raise e
                finally:
                    conn.close()

                catat_log(f"Opname Stok untuk {nama}: dari {stok_lama} menjadi {stok_baru}")

                self.load_barang()
                self.show_notif("Sukses", "Stok fisik berhasil disesuaikan beserta riwayat transaksinya.")
            except ValueError:
                self.show_notif("Gagal", "Stok harus berupa angka bulat!", is_error=True)
            except Exception as e:
                self.show_notif("Error", f"Terjadi kesalahan: {e}", is_error=True)

    def load_kategori(self):
        try:
            conn = get_connection(); cursor = conn.cursor(); cursor.execute("SELECT * FROM kategori")
            self.filter_kategori.clear(); self.filter_kategori.addItem("Semua Kategori")
            for r in cursor.fetchall(): 
                self.filter_kategori.addItem(r[1], r[0])
            conn.close()
        except Exception as e: print(f"Load Kategori Error: {e}")

    def generate_barcode_id(self):
        try:
            conn = get_connection(); cursor = conn.cursor(); cursor.execute("SELECT MAX(id_barang) FROM barang_baru")
            res = cursor.fetchone()[0] or 0; conn.close(); return f"BRG{(res + 1):05d}"
        except Exception as e: print(f"Generate Barcode ID Error: {e}"); return "BRG-ERR"

    def isi_form_dari_tabel(self, item):
        row = item.row()
        self.id_barang_aktif = self.table.item(row, 1).data(Qt.UserRole)
        self.barcode_manual.setText(self.table.item(row, 2).text())
        self.nama_barang.setText(self.table.item(row, 3).text())
        self.rak_input.setText(self.table.item(row, 4).text())
        self.kategori.setCurrentText(self.table.item(row, 5).text())
        self.lokasi.setCurrentText(self.table.item(row, 6).text())
        self.satuan.setText(self.table.item(row, 7).text())
        self.stok_minimum.setText(self.table.item(row, 8).text())

    def remove_barcode_file(self, code):
        clean = "".join(c for c in str(code) if c.isalnum() or c in (" ", "_")).replace(" ", "_")
        path = os.path.join(self.barcode_dir, f"{clean}.png")
        if os.path.exists(path):
            try: os.remove(path)
            except Exception as e: print(f"Remove Barcode File Error: {e}")

    def generate_barcode_image(self, code, name):
        try:
            options = {'font_path': self.font_path, 'font_size': 10, 'text_distance': 4.0, 'module_height': 15.0, 'center_text': True}
            clean = "".join(c for c in str(code) if c.isalnum() or c in (" ", "_")).replace(" ", "_")
            file_path = os.path.join(self.barcode_dir, clean)
            with open(f"{file_path}.png", "wb") as f:
                Code128(str(code), writer=ImageWriter()).write(f, options=options)
            return True
        except Exception as e: print(f"Generate Barcode Error: {e}"); return False

    def print_barcode_terpilih(self):
        row = self.table.currentRow()
        if row < 0: 
            self.show_notif("Peringatan", "Pilih barang yang ingin dicetak barcodenya.", is_error=True); return
        kode, nama = self.table.item(row, 2).text(), self.table.item(row, 3).text()
        clean = "".join(c for c in str(kode) if c.isalnum() or c in (" ", "_")).replace(" ", "_")
        path = os.path.abspath(os.path.join(self.barcode_dir, f"{clean}.png"))
        if not os.path.exists(path): self.generate_barcode_image(kode, nama)
        if os.path.exists(path):
            if os.name == 'nt': os.startfile(path, "print")

    def import_csv_massal(self):
        import csv
        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih File CSV Data Master", "", "CSV Files (*.csv)")
        if not file_path: return
        
        try:
            conn = get_connection(); cursor = conn.cursor()
            w_skrg = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            sukses = 0
            with open(file_path, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None) # Abaikan header (Nama, Kategori, Rak, dll)
                for row in reader:
                    if len(row) >= 5: # minimal: nama, kategori(id), lokasi(id), satuan, stok_min
                        kode_baru = self.generate_barcode_id()
                        kat_id, lok_id = row[1], row[2]
                        # Disini asumsi csv isi ID kategori & lokasi (integer), atau Anda perlu query mencari ID berdasarkan string.
                        # Untuk aman, jika insert gagal lompati
                        cursor.execute("""
                            INSERT INTO barang_baru (id_barang, nama_barang, id_kategori, id_lokasi, satuan, stok_minimum, stok)
                            VALUES (?, ?, ?, ?, ?, ?, 0)
                        """, (kode_baru, row[0], kat_id, lok_id, row[3], row[4]))
                        
                        # Generate dummy barcode 
                        cursor.execute("SELECT MAX(rowid) FROM barang_baru")
                        last_id = cursor.fetchone()[0]
                        kode_update = f"BRG{last_id:05d}"
                        cursor.execute("UPDATE barang_baru SET id_barang=? WHERE rowid=?", (kode_update, last_id))
                        self.generate_barcode_image(kode_update, row[0])
                        sukses += 1
            conn.commit(); conn.close()
            catat_log(f"Mengimpor CSV secara massal: {sukses} barang berhasil ditambahkan")
            self.load_barang()
            self.show_notif("Berhasil", f"Total {sukses} data barang berhasil diimpor.")
        except Exception as e:
            self.show_notif("Gagal", f"Format CSV tidak valid atau terjadi error: {e}", is_error=True)

    def cetak_barcode_terpilih_massal(self):
        # Ambil data yang hanya dicentang
        items_to_print = []
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0).checkState() == Qt.Checked:
                items_to_print.append({
                    "kode": self.table.item(r, 2).text(),
                    "nama": self.table.item(r, 3).text()
                })
        
        if not items_to_print:
            self.show_notif("Peringatan", "Silakan centang barang yang ingin dicetak barcodenya.", is_error=True); return
            
        self._generate_barcode_pdf(items_to_print, f"Barcode_Terpilih_{len(items_to_print)}_Item.pdf")

    def cetak_semua_barcode(self):
        items_to_print = []
        for r in range(self.table.rowCount()):
            items_to_print.append({
                "kode": self.table.item(r, 2).text(),
                "nama": self.table.item(r, 3).text()
            })
        
        if not items_to_print:
            self.show_notif("Peringatan", "Tidak ada data barang untuk dicetak.", is_error=True); return
            
        self._generate_barcode_pdf(items_to_print, "Barcode_Semua_Barang.pdf")

    def _generate_barcode_pdf(self, items, default_name):
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Image as RLImage, Spacer, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        import os

        file_path, _ = QFileDialog.getSaveFileName(self, "Simpan PDF Barcode", default_name, "PDF Files (*.pdf)")
        if not file_path: return

        try:
            doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            elements = []
            styles = getSampleStyleSheet()
            
            elements.append(Paragraph(f"<b>DAFTAR BARCODE ({len(items)} ITEM)</b>", styles['Title']))
            elements.append(Spacer(1, 20))
            
            for item in items:
                kode = item["kode"]
                nama = item["nama"]
                clean = "".join(c for c in str(kode) if c.isalnum() or c in (" ", "_")).replace(" ", "_")
                img_path = os.path.abspath(os.path.join(self.barcode_dir, f"{clean}.png"))
                
                if not os.path.exists(img_path):
                    self.generate_barcode_image(kode, nama)
                
                if os.path.exists(img_path):
                    elements.append(Paragraph(f"<b>{kode} - {nama}</b>", styles['Normal']))
                    elements.append(Spacer(1, 5))
                    elements.append(RLImage(img_path, width=150, height=50))
                    elements.append(Spacer(1, 15))
            
            doc.build(elements)
            self.show_notif("Berhasil", f"PDF barcode tersimpan di:\n{file_path}")
            if os.name == 'nt': os.startfile(file_path)
        except Exception as e:
            self.show_notif("Error", f"Gagal membuat PDF barcode: {e}", is_error=True)