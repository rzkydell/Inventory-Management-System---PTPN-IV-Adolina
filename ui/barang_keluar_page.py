import os
import sqlite3
import cv2
import winsound
import sys
from pyzbar import pyzbar
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QCheckBox,
    QTableWidgetItem, QMessageBox, QHeaderView,
    QAbstractItemView, QFrame, QScrollArea, QGridLayout, QSizePolicy, QCompleter
)
from PySide6.QtCore import Qt, QSettings, QStringListModel
from database.connection import get_connection, catat_log
from datetime import datetime

class BarangKeluarPage(QWidget):
    """
    Halaman Pencatatan Barang Keluar (FIFO System).
    Dioptimalkan untuk responsivitas pada laptop layar kecil (12 inch).
    """
    def __init__(self):
        super().__init__()
        self.batch_pemandu = None 
        self.total_stok_tersedia = 0 
        self.metode_input = "MANUAL"
        self.settings = QSettings("PTPN4_Inventaris", "SessionState")
        self.init_ui()

    def showEvent(self, event):
        """Refresh data saat tab dibuka"""
        super().showEvent(event)
        self.clear_form()
        self.load_transaksi()
        self.update_penerima_autocomplete()

    def update_penerima_autocomplete(self):
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT keterangan FROM transaksi WHERE jenis='KELUAR' AND keterangan != '-' AND keterangan IS NOT NULL")
            penerimas = [r[0] for r in cursor.fetchall() if r[0].strip()]
            self.penerima_model.setStringList(penerimas)
            conn.close()
        except: pass

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # --- MANDATORY SCROLL AREA ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #fcf8f8; }")
        
        container = QWidget()
        container.setStyleSheet("background-color: #fcf8f8;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Global Style - Red Theme
        self.setStyleSheet("""
            QWidget { font-family: 'Segoe UI', Arial; font-size: 13px; color: #1e293b; }
            QLabel { color: #475569; font-weight: 700; }
            QLineEdit { 
                background-color: white; border: 1px solid #e2e8f0; 
                border-radius: 8px; padding: 10px; color: #1e293b;
            }
            QLineEdit:focus { border: 2px solid #ef4444; }
            QPushButton { border-radius: 8px; font-weight: bold; }
        """)

        # --- SECTION 1: SEARCH & SCAN ---
        top_bar_card = QFrame()
        top_bar_card.setStyleSheet("background-color: white; border-radius: 16px; border: 1px solid #e2e8f0;")
        self.apply_shadow(top_bar_card)
        top_bar_layout = QHBoxLayout(top_bar_card)
        top_bar_layout.setContentsMargins(15, 15, 15, 15)
        
        self.input_barcode = QLineEdit()
        self.input_barcode.setPlaceholderText("🔍 Scan Barcode pengeluaran...")
        self.input_barcode.setFixedHeight(40)
        self.input_barcode.returnPressed.connect(self.cari_barang_manual)

        btn_cari = QPushButton("CARI DATA")
        btn_cari.setFixedSize(110, 40)
        btn_cari.setCursor(Qt.PointingHandCursor)
        btn_cari.setStyleSheet("background-color: #1e293b; color: white;")
        btn_cari.clicked.connect(self.cari_barang_manual)

        btn_scan_kamera = QPushButton("📷 SCAN")
        btn_scan_kamera.setFixedSize(120, 40)
        btn_scan_kamera.setCursor(Qt.PointingHandCursor)
        btn_scan_kamera.setStyleSheet("background-color: #ef4444; color: white;")
        btn_scan_kamera.clicked.connect(self.scan_via_kamera)

        top_bar_layout.addWidget(self.input_barcode, 1)
        top_bar_layout.addWidget(btn_cari)
        top_bar_layout.addWidget(btn_scan_kamera)
        layout.addWidget(top_bar_card)

        # --- SECTION 2: DETAIL FIFO PEMANDU ---
        detail_card = QFrame()
        detail_card.setStyleSheet("background-color: white; border-radius: 16px; border: 1px solid #e2e8f0;")
        self.apply_shadow(detail_card)
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(20, 20, 20, 20)

        detail_layout.addWidget(QLabel("📦 PANDUAN PENGAMBILAN (FIFO)", styleSheet="color: #b91c1c; font-size: 13px; letter-spacing: 0.5px;"))

        info_grid = QGridLayout()
        info_grid.setSpacing(12)
        label_s = "color: #64748b; font-size: 11px; text-transform: uppercase; font-weight: 800;"
        val_s = "background-color: #fffaf0; font-weight: 700; color: #1e293b; border: 1px solid #fed7aa; padding: 10px;"

        info_grid.addWidget(QLabel("NAMA BARANG", styleSheet=label_s), 0, 0)
        self.nama_barang = QLineEdit(); self.nama_barang.setReadOnly(True); self.nama_barang.setStyleSheet(val_s)
        info_grid.addWidget(self.nama_barang, 1, 0)

        info_grid.addWidget(QLabel("LOKASI RAK", styleSheet=label_s), 0, 1)
        self.rak_pemandu = QLineEdit(); self.rak_pemandu.setReadOnly(True); self.rak_pemandu.setStyleSheet(val_s)
        info_grid.addWidget(self.rak_pemandu, 1, 1)

        info_grid.addWidget(QLabel("LOKASI SLOT", styleSheet=label_s), 2, 0)
        self.slot_pemandu = QLineEdit(); self.slot_pemandu.setReadOnly(True); self.slot_pemandu.setStyleSheet(val_s)
        info_grid.addWidget(self.slot_pemandu, 3, 0)

        info_grid.addWidget(QLabel("TGL MASUK BATCH", styleSheet=label_s), 2, 1)
        self.tgl_masuk_pemandu = QLineEdit(); self.tgl_masuk_pemandu.setReadOnly(True); self.tgl_masuk_pemandu.setStyleSheet(val_s)
        info_grid.addWidget(self.tgl_masuk_pemandu, 3, 1)

        # Stok Display (Proporsional)
        info_grid.addWidget(QLabel("TOTAL STOK", styleSheet=label_s), 0, 2)
        self.stok_display = QLineEdit(); self.stok_display.setReadOnly(True)
        self.stok_display.setFixedSize(110, 85)
        self.stok_display.setAlignment(Qt.AlignCenter)
        self.stok_display.setStyleSheet("""
            background-color: #fef2f2; border: 2px solid #fecaca; 
            border-radius: 12px; color: #b91c1c; font-size: 28px; font-weight: 800;
        """)
        info_grid.addWidget(self.stok_display, 1, 2, 3, 1)

        detail_layout.addLayout(info_grid)
        detail_layout.addSpacing(10)

        # Qty Input & Action (Ramping)
        action_layout = QHBoxLayout()
        
        v_ket = QVBoxLayout()
        v_ket.addWidget(QLabel("PENERIMA", styleSheet=label_s))
        self.keterangan_input = QLineEdit()
        self.keterangan_input.setPlaceholderText("Wajib: Nama Penerima")
        self.keterangan_input.setFixedHeight(50)
        self.keterangan_input.setStyleSheet("font-size: 14px; background-color: #f8fafc;")
        
        self.penerima_model = QStringListModel()
        self.penerima_completer = QCompleter(self.penerima_model, self)
        self.penerima_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.penerima_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.keterangan_input.setCompleter(self.penerima_completer)
        
        v_ket.addWidget(self.keterangan_input)
        action_layout.addLayout(v_ket, 2)

        v_qty = QVBoxLayout()
        v_qty.addWidget(QLabel("JUMLAH KELUAR", styleSheet=label_s))
        self.jumlah = QLineEdit(); self.jumlah.setText("0")
        self.jumlah.setFixedHeight(50)
        self.jumlah.setAlignment(Qt.AlignCenter)
        self.jumlah.setStyleSheet("""
            font-size: 24px; font-weight: 800; border: 2px solid #ef4444; 
            color: #b91c1c; background: #fff1f2; border-radius: 8px;
        """)
        self.jumlah.textChanged.connect(self.validasi_input_manual)
        v_qty.addWidget(self.jumlah)
        
        self.chk_surat_jalan = QCheckBox("🖨️ Cetak Surat Jalan (DO)")
        self.chk_surat_jalan.setChecked(True)
        self.chk_surat_jalan.setStyleSheet("color: #1e293b; font-weight: bold; font-size: 11px; margin-top: 5px;")
        v_qty.addWidget(self.chk_surat_jalan)
        
        action_layout.addLayout(v_qty, 1)

        self.btn_simpan = QPushButton("🚨 SIMPAN PENGELUARAN")
        self.btn_simpan.setFixedHeight(70); self.btn_simpan.setCursor(Qt.PointingHandCursor)
        self.btn_simpan.setStyleSheet("""
            QPushButton { background-color: #ef4444; color: white; font-size: 14px; font-weight: 800; border-radius: 8px; margin-top: 5px; }
            QPushButton:hover { background-color: #dc2626; }
        """)
        self.btn_simpan.clicked.connect(self.simpan_transaksi)
        action_layout.addWidget(self.btn_simpan, 2)
        
        detail_layout.addLayout(action_layout)
        layout.addWidget(detail_card)

        # --- SECTION 3: TABLE RIWAYAT ---
        history_header = QHBoxLayout()
        history_header.addWidget(QLabel("📋 RIWAYAT PENGELUARAN SESI INI", styleSheet="font-size: 13px; font-weight: 800; color: #1e293b;"))
        history_header.addStretch()
        btn_clr = QPushButton("🧹 BERSIHKAN")
        btn_clr.setCursor(Qt.PointingHandCursor)
        btn_clr.setStyleSheet("background-color: #94a3b8; color: white; padding: 6px 12px; font-size: 11px; border-radius: 6px;")
        btn_clr.clicked.connect(self.bersihkan_tampilan_tabel)
        history_header.addWidget(btn_clr); layout.addLayout(history_header)

        self.table = QTableWidget()
        self.table.setMinimumHeight(250)
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(["WAKTU", "KODE", "BARANG", "RAK", "SLOT", "QTY", "AWAL", "AKHIR", "PENERIMA"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget { background-color: white; border-radius: 16px; border: 1px solid #e2e8f0; gridline-color: #f1f5f9; }
            QHeaderView::section { background: #fcf8f8; color: #475569; font-weight: bold; border: none; border-bottom: 2px solid #e2e8f0; padding: 12px; }
            QTableWidget::item { padding: 5px; }
            QTableWidget::item:selected { background-color: #fef2f2; color: #1e293b; }
        """)
        self.apply_shadow(self.table)
        layout.addWidget(self.table, 1)

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
        """Standardized notification box with black text and white background"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title); msg.setText(text)
        msg.setIcon(QMessageBox.Critical if is_error else QMessageBox.Information)
        msg.setStyleSheet("""
            QMessageBox { background-color: white; } 
            QLabel { color: black; font-size: 13px; font-weight: normal; } 
            QPushButton { color: black; font-weight: bold; background-color: #f1f5f9; border: 1px solid #cbd5e1; min-width: 70px; padding: 5px; }
        """)
        msg.exec()

    def cari_barang_manual(self):
        barcode = self.input_barcode.text().strip()
        self.metode_input = "MANUAL"
        if self.cari_fifo_logic(barcode):
            self.jumlah.setFocus(); self.jumlah.selectAll()

    def cari_fifo_logic(self, barcode_val):
        if not barcode_val: return False
        try:
            conn = get_connection(); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(t.sisa_qty) as total 
                FROM transaksi t JOIN barang_baru b ON t.id_barang = b.id_barang
                WHERE b.barcode = ? AND t.jenis = 'MASUK' AND t.sisa_qty > 0
            """, (barcode_val,))
            res = cursor.fetchone()
            self.total_stok_tersedia = res["total"] if res["total"] is not None else 0

            if self.total_stok_tersedia <= 0:
                self.show_notif("Stok Habis", f"Stok barang {barcode_val} sudah habis!", is_error=True)
                conn.close(); return False

            cursor.execute("""
                SELECT t.id_transaksi, t.id_barang, t.tanggal, t.sisa_qty, 
                       b.nama_barang, b.rak, l.nama_lokasi as slot
                FROM transaksi t
                JOIN barang_baru b ON t.id_barang = b.id_barang
                LEFT JOIN lokasi l ON b.id_lokasi = l.id_lokasi
                WHERE b.barcode = ? AND t.jenis = 'MASUK' AND t.sisa_qty > 0
                ORDER BY t.tanggal ASC LIMIT 1
            """, (barcode_val,))
            row = cursor.fetchone()
            if row:
                self.batch_pemandu = {"id_tr": row["id_transaksi"], "id_br": row["id_barang"], "sisa": row["sisa_qty"], "slot": row["slot"]}
                self.nama_barang.setText(row["nama_barang"])
                self.rak_pemandu.setText(row["rak"] or "-")
                self.slot_pemandu.setText(row["slot"])
                self.tgl_masuk_pemandu.setText(row["tanggal"])
                self.stok_display.setText(str(self.total_stok_tersedia))
                conn.close(); return True
            conn.close(); return False
        except: return False

    def validasi_input_manual(self, text):
        if not self.total_stok_tersedia or not text.isdigit(): return
        qty_input = int(text)
        if qty_input > self.total_stok_tersedia:
            winsound.Beep(500, 500)
            self.show_notif("Peringatan Stok", f"Jumlah melebihi total stok yang ada ({self.total_stok_tersedia} tersedia).", is_error=True)
            self.jumlah.setText(str(self.total_stok_tersedia))

    def simpan_transaksi(self):
        if not self.input_barcode.text(): return
        try:
            total_qty_input = int(self.jumlah.text() or 0)
            if total_qty_input <= 0: return
            if total_qty_input > self.total_stok_tersedia:
                self.show_notif("Gagal", "Jumlah melebihi stok tersedia!", is_error=True); return
            
            ket = self.keterangan_input.text().strip()
            if not ket:
                self.show_notif("Peringatan", "Nama Penerima Wajib Diisi!", is_error=True); return
                
            self.proses_multi_slot(total_qty_input)
        except Exception as e: self.show_notif("Error", str(e), is_error=True)

    def proses_multi_slot(self, total_qty):
        barcode = self.input_barcode.text().strip()
        conn = get_connection(); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id_transaksi, t.id_barang, t.sisa_qty, l.nama_lokasi as slot
            FROM transaksi t JOIN barang_baru b ON t.id_barang = b.id_barang
            LEFT JOIN lokasi l ON b.id_lokasi = l.id_lokasi
            WHERE b.barcode = ? AND t.jenis = 'MASUK' AND t.sisa_qty > 0
            ORDER BY t.tanggal ASC
        """, (barcode,))
        
        batches = cursor.fetchall()
        sisa_hitung = total_qty
        rencana_potong = []
        ringkasan_slot = {} 

        for b in batches:
            if sisa_hitung <= 0: break
            ambil = min(b["sisa_qty"], sisa_hitung)
            rencana_potong.append({"id_tr": b["id_transaksi"], "id_br": b["id_barang"], "qty": ambil, "sisa_awal": b["sisa_qty"]})
            nama_slot = b['slot']
            ringkasan_slot[nama_slot] = ringkasan_slot.get(nama_slot, 0) + ambil
            sisa_hitung -= ambil

        msg_text = "KONFIRMASI PENGELUARAN (FIFO):\n\n"
        for slot, t_ambil in ringkasan_slot.items():
            msg_text += f"• Ambil {t_ambil} unit dari Slot: {slot}\n"

        msg = QMessageBox(self)
        msg.setWindowTitle("Konfirmasi Keluar")
        msg.setText(msg_text + f"\nTOTAL: {total_qty} UNIT")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setStyleSheet("QMessageBox { background-color: white; } QLabel { color: black; } QPushButton { color: black; min-width: 60px; }")
        
        if msg.exec() == QMessageBox.Yes:
            w_skrg = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ket = self.keterangan_input.text().strip()
            try:
                for p in rencana_potong:
                    cursor.execute("UPDATE transaksi SET sisa_qty = sisa_qty - ? WHERE id_transaksi = ?", (p["qty"], p["id_tr"]))
                    cursor.execute("UPDATE barang_baru SET stok = stok - ? WHERE id_barang = ?", (p["qty"], p["id_br"]))
                    cursor.execute("""
                        INSERT INTO transaksi (id_barang, jenis, stok_sebelum, stok_sesudah, metode, tanggal, keterangan)
                        VALUES (?, 'KELUAR', ?, ?, ?, ?, ?)
                    """, (p["id_br"], p["sisa_awal"], p["sisa_awal"] - p["qty"], self.metode_input, w_skrg, ket))
                conn.commit()
                catat_log(f"Barang Keluar: {ket} menerima -{total_qty} {self.nama_barang.text()} via FIFO")
            except Exception as e:
                conn.rollback(); raise e
            finally:
                conn.close()
            
            self.show_notif("Berhasil", "Data pengeluaran telah diproses.")
            
            if self.chk_surat_jalan.isChecked():
                self.generate_surat_jalan(ket, total_qty, ringkasan_slot)

            self.clear_form(); self.load_transaksi()
        else:
            conn.close()

    def generate_surat_jalan(self, penerima, total_qty, ringkasan_slot):
        from reportlab.lib.pagesizes import A5
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        
        os.makedirs("DO", exist_ok=True)
        doc_name = os.path.join("DO", f"DO_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
        try:
            doc = SimpleDocTemplate(doc_name, pagesize=A5, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
            elements = []
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('Title', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=14, alignment=1)
            
            elements.append(Paragraph("<b>SURAT JALAN / DELIVERY ORDER</b>", title_style))
            elements.append(Paragraph("PTPN IV KEBUN ADOLINA", styles['Normal']))
            elements.append(Spacer(1, 15))
            
            elements.append(Paragraph(f"<b>Tanggal:</b> {datetime.now().strftime('%d %B %Y %H:%M:%S')}", styles['Normal']))
            elements.append(Paragraph(f"<b>Penerima:</b> {penerima}", styles['Normal']))
            elements.append(Spacer(1, 10))
            
            data = [["Nama Barang", "Slot Diambil", "Jumlah"]]
            for slot, qty in ringkasan_slot.items():
                data.append([self.nama_barang.text(), slot, str(qty)])
            
            data.append(["", "TOTAL:", str(total_qty)])
            
            t = Table(data, colWidths=[120, 80, 60])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#ef4444")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('BACKGROUND', (0,1), (-1,-1), colors.white),
                ('GRID', (0,0), (-1,-2), 1, colors.black),
                ('LINEABOVE', (0,-1), (-1,-1), 1, colors.black),
                ('FONTNAME', (1,-1), (1,-1), 'Helvetica-Bold')
            ]))
            elements.append(t)
            elements.append(Spacer(1, 30))
            elements.append(Paragraph("_____________________<br/>(Tanda Tangan Penerima)", styles['Normal']))
            
            doc.build(elements)
            if os.name == 'nt': os.startfile(doc_name)
        except Exception as e:
            self.show_notif("Gagal PDF", str(e), is_error=True)

    def scan_via_kamera(self):
        cap = cv2.VideoCapture(0)
        while True:
            ret, frame = cap.read()
            if not ret: break
            bv = None
            for obj in pyzbar.decode(frame): bv = obj.data.decode('utf-8'); break
            cv2.imshow("PTPN IV SCANNER (ESC: Keluar)", frame)
            if bv:
                winsound.Beep(1000, 150); self.metode_input = "SCAN"
                if self.input_barcode.text() == bv:
                    current_qty = int(self.jumlah.text() or 0)
                    if current_qty + 1 > self.total_stok_tersedia:
                        winsound.Beep(500, 1000)
                        self.show_notif("Peringatan Stok", f"Jumlah sudah maksimal ({self.total_stok_tersedia} tersedia).", is_error=True)
                    else:
                        self.jumlah.setText(str(current_qty + 1))
                else:
                    self.input_barcode.setText(bv)
                    if self.cari_fifo_logic(bv): self.jumlah.setText("1")
                cv2.waitKey(1000) 
            if cv2.waitKey(1) & 0xFF == 27: break 
        cap.release(); cv2.destroyAllWindows()

    def clear_form(self):
        self.batch_pemandu = None; self.total_stok_tersedia = 0
        self.input_barcode.clear(); self.nama_barang.clear(); self.rak_pemandu.clear()
        self.slot_pemandu.clear(); self.tgl_masuk_pemandu.clear(); self.stok_display.clear()
        self.keterangan_input.clear(); self.jumlah.setText("0"); self.input_barcode.setFocus()

    def bersihkan_tampilan_tabel(self):
        self.settings.setValue("checkpoint_keluar", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        self.table.setRowCount(0); self.show_notif("Info", "Tampilan riwayat dibersihkan.")

    def load_transaksi(self):
        try:
            cp = self.settings.value("checkpoint_keluar", "2000-01-01 00:00:00")
            conn = get_connection(); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
            cursor.execute("""
                SELECT t.tanggal, b.barcode, b.nama_barang, b.rak, l.nama_lokasi as slot,
                       (t.stok_sebelum - t.stok_sesudah) as qty, t.stok_sebelum, t.stok_sesudah, t.keterangan
                FROM transaksi t 
                JOIN barang_baru b ON t.id_barang = b.id_barang 
                LEFT JOIN lokasi l ON b.id_lokasi = l.id_lokasi
                WHERE t.jenis = 'KELUAR' AND t.tanggal > ? ORDER BY t.tanggal DESC LIMIT 200
            """, (cp,))
            rows = cursor.fetchall(); self.table.setRowCount(0)
            for i, row in enumerate(rows):
                self.table.insertRow(i)
                data = [str(row["tanggal"]), str(row["barcode"]), str(row["nama_barang"]), str(row["rak"]), str(row["slot"]), f"-{row['qty']}", str(row["stok_sebelum"]), str(row["stok_sesudah"]), str(row["keterangan"] or "-")]
                for col, text in enumerate(data):
                    ti = QTableWidgetItem(text)
                    if col >= 5: ti.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(i, col, ti)
            conn.close()
        except: pass