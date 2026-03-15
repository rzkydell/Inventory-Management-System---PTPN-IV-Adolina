import csv
import os
import sqlite3
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QFileDialog, QMessageBox, QFrame, QLineEdit,
    QAbstractItemView, QScrollArea, QSizePolicy, QDateEdit
)
from PySide6.QtCore import Qt, QDate
from database.connection import get_connection, catat_log
from datetime import datetime, timedelta

# Library untuk Excel
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, Reference

# Library untuk PDF
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, PageBreak
from reportlab.platypus import Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

class LaporanPage(QWidget):
    """
    Halaman Laporan Inventaris PTPN IV.
    Dioptimalkan untuk responsivitas pada laptop layar kecil (12 inch).
    """
    def __init__(self):
        super().__init__()
        self.init_ui()

    def showEvent(self, event):
        """Refresh data otomatis saat halaman dibuka"""
        super().showEvent(event)
        self.load_laporan()

    def init_ui(self):
        # Layout utama tanpa margin agar ScrollArea menempel ke pinggir
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
            QComboBox, QLineEdit { 
                color: #1e293b; background-color: white; border: 1px solid #e2e8f0; 
                border-radius: 8px; padding: 8px; 
            }
            QComboBox:focus, QLineEdit:focus { border: 2px solid #3b82f6; }
        """)

        # --- HEADER & FILTER BAR ---
        top_bar_card = QFrame()
        top_bar_card.setStyleSheet("background-color: white; border-radius: 16px; border: 1px solid #e2e8f0;")
        self.apply_shadow(top_bar_card)
        top_bar = QHBoxLayout(top_bar_card)
        top_bar.setContentsMargins(15, 12, 15, 12)
        top_bar.setSpacing(8)

        self.input_cari = QLineEdit()
        self.input_cari.setPlaceholderText("🔍 Cari Nama/Kode...")
        self.input_cari.setMinimumWidth(120)
        self.input_cari.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_cari.textChanged.connect(self.filter_tabel_internal)

        self.filter_periode = QComboBox()
        self.filter_periode.addItems(["Hari Ini", "Minggu Ini", "Bulan Ini", "Tahun Ini", "Semua Waktu", "Custom Tanggal"])
        self.filter_periode.setMinimumWidth(120)
        self.filter_periode.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.filter_periode.currentIndexChanged.connect(self.on_periode_changed)
        
        # Custom Date Pickers
        date_style = "QDateEdit { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 5px; color: #1e293b; }"
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate())
        self.date_from.setStyleSheet(date_style)
        self.date_from.hide()
        self.date_from.dateChanged.connect(self.load_laporan)
        
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setStyleSheet(date_style)
        self.date_to.hide()
        self.date_to.dateChanged.connect(self.load_laporan)

        self.filter_jenis = QComboBox()
        self.filter_jenis.addItems(["Barang Masuk", "Barang Keluar", "Ringkasan Semua", "Analisis Pergerakan Barang"])
        self.filter_jenis.setMinimumWidth(180)
        self.filter_jenis.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.filter_jenis.currentIndexChanged.connect(self.load_laporan)

        # Action Buttons Styling (Dibuat Ramping)
        btn_base = "color: white; padding: 8px 12px; border-radius: 8px; font-weight: bold; font-size: 11px;"
        
        self.btn_excel = QPushButton("📊 EXPORT EXCEL")
        self.btn_excel.setStyleSheet(f"background-color: #10b981; {btn_base}")
        self.btn_excel.clicked.connect(self.export_to_excel)

        self.btn_pdf = QPushButton("🖨️ CETAK PDF")
        self.btn_pdf.setStyleSheet(f"background-color: #ef4444; {btn_base}")
        self.btn_pdf.clicked.connect(self.export_to_pdf)

        for b in [self.btn_excel, self.btn_pdf]:
            b.setCursor(Qt.PointingHandCursor)

        top_bar.addWidget(QLabel("CARI:"))
        top_bar.addWidget(self.input_cari)
        top_bar.addSpacing(10)
        top_bar.addWidget(QLabel("PERIODE:"))
        top_bar.addWidget(self.filter_periode)
        top_bar.addWidget(self.date_from)
        top_bar.addWidget(self.date_to)
        top_bar.addSpacing(10)
        top_bar.addWidget(QLabel("JENIS:"))
        top_bar.addWidget(self.filter_jenis)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_excel)
        top_bar.addWidget(self.btn_pdf)
        layout.addWidget(top_bar_card)

        # --- STATISTIC CARDS (KPI) ---
        stats_layout = QHBoxLayout()
        self.card_masuk = self.create_stat_card("RINGKASAN MASUK", "0x", "Total: 0 Unit", "#ecfdf5", "#047857")
        self.card_keluar = self.create_stat_card("RINGKASAN KELUAR", "0x", "Total: 0 Unit", "#fff1f2", "#b91c1c")
        stats_layout.addWidget(self.card_masuk); stats_layout.addWidget(self.card_keluar)
        layout.addLayout(stats_layout)

        # --- TABLE SECTION ---
        self.table = QTableWidget()
        self.table.setMinimumHeight(250) # Agar tidak gepeng di layar kecil
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Tanggal", "Kode", "Nama Barang", "Kategori", "RAK", "SLOT", "Qty Masuk", "Suplier"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget { background: white; border-radius: 16px; border: 1px solid #e2e8f0; color: #1e293b; gridline-color: #f1f5f9; }
            QHeaderView::section { background: #f8fafc; color: #475569; font-weight: bold; padding: 12px; border: none; border-bottom: 2px solid #e2e8f0; }
            QTableWidget::item { padding: 5px; }
            QTableWidget::item:selected { background-color: #eff6ff; color: #1e293b; }
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

    def create_stat_card(self, title, count_text, total_text, bg_color, text_color):
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background-color: {bg_color}; border-radius: 16px; border: 1px solid #cbd5e0; }}")
        self.apply_shadow(card)
        l = QVBoxLayout(card)
        l.setContentsMargins(15, 10, 15, 10)
        lbl_t = QLabel(title); lbl_t.setStyleSheet(f"color: {text_color}; font-size: 13px; font-weight: 800;")
        c = QLabel(count_text); c.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {text_color};")
        tt = QLabel(total_text); tt.setStyleSheet(f"color: {text_color}; font-weight: 600; font-size: 11px;")
        l.addWidget(lbl_t); l.addWidget(c); l.addWidget(tt)
        card.count_label = c; card.total_label = tt; return card

    def show_notif(self, title, text, is_error=False):
        """Standardized notification box with black text"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title); msg.setText(text)
        msg.setIcon(QMessageBox.Critical if is_error else QMessageBox.Information)
        msg.setStyleSheet("""
            QMessageBox { background-color: white; } 
            QLabel { color: black; font-size: 13px; font-weight: normal; } 
            QPushButton { color: black; font-weight: bold; background-color: #f1f5f9; border: 1px solid #cbd5e1; min-width: 70px; padding: 5px; }
        """)
        msg.exec()

    def on_periode_changed(self):
        if self.filter_periode.currentText() == "Custom Tanggal":
            self.date_from.show()
            self.date_to.show()
        else:
            self.date_from.hide()
            self.date_to.hide()
        self.load_laporan()

    def load_laporan(self):
        try:
            jenis = self.filter_jenis.currentText()
            
            # Reset headers if analysis is selected
            if jenis == "Analisis Pergerakan Barang":
                self.table.setColumnCount(8)
                self.table.setHorizontalHeaderLabels(["Kode Barcode", "Nama Barang", "Kategori", "RAK", "SLOT", "Stok Sisa", "Status", "Alasan"])
                self.load_analisis_pergerakan()
                return
            else:
                # Set column count and headers for other report types
                if jenis == "Barang Masuk":
                    self.table.setColumnCount(8)
                    self.table.setHorizontalHeaderLabels(["Tanggal", "Kode", "Nama Barang", "Kategori", "RAK", "SLOT", "Qty Masuk", "Suplier"])
                elif jenis == "Barang Keluar":
                    self.table.setColumnCount(8)
                    self.table.setHorizontalHeaderLabels(["Tanggal", "Kode", "Nama Barang", "Kategori", "RAK", "SLOT", "Qty Keluar", "Penerima"])
                else: # "Ringkasan Semua"
                    self.table.setColumnCount(9)
                    self.table.setHorizontalHeaderLabels(["Waktu Terakhir", "Kode", "Nama Barang", "Kategori", "RAK", "SLOT", "Masuk", "Keluar", "Sisa Stok"])

            import sqlite3 # Import here to avoid circular dependency if connection.py also imports PySide6
            conn = get_connection(); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
            idx = self.filter_periode.currentIndex()
            now = datetime.now()
            
            if idx == 0: date_f = f"t.tanggal LIKE '{now.strftime('%Y-%m-%d')}%'"
            elif idx == 1: date_f = f"t.tanggal >= '{(now - timedelta(days=7)).strftime('%Y-%m-%d')}'"
            elif idx == 2: date_f = f"t.tanggal >= '{(now - timedelta(days=30)).strftime('%Y-%m-%d')}'"
            elif idx == 3: date_f = f"t.tanggal >= '{(now - timedelta(days=365)).strftime('%Y-%m-%d')}'"
            elif idx == 5: 
                start = self.date_from.date().toString("yyyy-MM-dd")
                end = self.date_to.date().toString("yyyy-MM-dd")
                date_f = f"t.tanggal >= '{start} 00:00:00' AND t.tanggal <= '{end} 23:59:59'"
            else: date_f = "1=1"

            cursor.execute(f"SELECT jenis, COUNT(*), SUM(ABS(stok_sesudah - stok_sebelum)) FROM transaksi t WHERE {date_f} GROUP BY jenis")
            stats = cursor.fetchall()
            self.card_masuk.count_label.setText("0x"); self.card_masuk.total_label.setText("Total: 0 Unit")
            self.card_keluar.count_label.setText("0x"); self.card_keluar.total_label.setText("Total: 0 Unit")
            for s in stats:
                if s[0] == "MASUK": self.card_masuk.count_label.setText(f"{s[1]}x"); self.card_masuk.total_label.setText(f"Total: {s[2] or 0} Unit")
                elif s[0] == "KELUAR": self.card_keluar.count_label.setText(f"{s[1]}x"); self.card_keluar.total_label.setText(f"Total: {s[2] or 0} Unit")

            jenis_laporan = self.filter_jenis.currentIndex() # 0: Masuk, 1: Keluar, 2: Semua
            
            if jenis_laporan == 0:
                self.table.setColumnCount(8)
                self.table.setHorizontalHeaderLabels(["Tanggal", "Kode", "Nama Barang", "Kategori", "RAK", "SLOT", "Qty Masuk", "Suplier"])
                query = f"""
                    SELECT t.tanggal as waktu, b.barcode, b.nama_barang, 
                           COALESCE(k.nama_kategori, '-') as kat, COALESCE(b.rak, '-') as rk, COALESCE(l.nama_lokasi, '-') as sl,
                           ABS(t.stok_sesudah - t.stok_sebelum) as qty, COALESCE(t.keterangan, '-') as ket
                    FROM transaksi t 
                    JOIN barang_baru b ON t.id_barang = b.id_barang 
                    LEFT JOIN kategori k ON b.id_kategori = k.id_kategori LEFT JOIN lokasi l ON b.id_lokasi = l.id_lokasi
                    WHERE {date_f} AND t.jenis = 'MASUK'
                    ORDER BY t.tanggal DESC
                """
            elif jenis_laporan == 1:
                self.table.setColumnCount(8)
                self.table.setHorizontalHeaderLabels(["Tanggal", "Kode", "Nama Barang", "Kategori", "RAK", "SLOT", "Qty Keluar", "Penerima"])
                query = f"""
                    SELECT t.tanggal as waktu, b.barcode, b.nama_barang, 
                           COALESCE(k.nama_kategori, '-') as kat, COALESCE(b.rak, '-') as rk, COALESCE(l.nama_lokasi, '-') as sl,
                           ABS(t.stok_sebelum - t.stok_sesudah) as qty, COALESCE(t.keterangan, '-') as ket
                    FROM transaksi t 
                    JOIN barang_baru b ON t.id_barang = b.id_barang 
                    LEFT JOIN kategori k ON b.id_kategori = k.id_kategori LEFT JOIN lokasi l ON b.id_lokasi = l.id_lokasi
                    WHERE {date_f} AND t.jenis = 'KELUAR'
                    ORDER BY t.tanggal DESC
                """
            else:
                self.table.setColumnCount(9)
                self.table.setHorizontalHeaderLabels(["Waktu Terakhir", "Kode", "Nama Barang", "Kategori", "RAK", "SLOT", "Masuk", "Keluar", "Sisa Stok"])
                query = f"""
                    SELECT MAX(t.tanggal) as waktu, b.barcode, b.nama_barang, 
                           COALESCE(k.nama_kategori, '-') as kat, COALESCE(b.rak, '-') as rk, COALESCE(l.nama_lokasi, '-') as sl,
                           SUM(CASE WHEN t.jenis = 'MASUK' THEN ABS(t.stok_sesudah - t.stok_sebelum) ELSE 0 END) as in_q,
                           SUM(CASE WHEN t.jenis = 'KELUAR' THEN ABS(t.stok_sesudah - t.stok_sebelum) ELSE 0 END) as out_q, b.stok
                    FROM barang_baru b 
                    LEFT JOIN transaksi t ON b.id_barang = t.id_barang AND {date_f}
                    LEFT JOIN kategori k ON b.id_kategori = k.id_kategori LEFT JOIN lokasi l ON b.id_lokasi = l.id_lokasi
                    GROUP BY b.id_barang HAVING (in_q > 0 OR out_q > 0 OR {1 if idx == 4 else 0})
                    ORDER BY waktu DESC
                """

            cursor.execute(query); rows = cursor.fetchall(); self.table.setRowCount(0)
            for i, r in enumerate(rows):
                self.table.insertRow(i)
                if jenis_laporan in [0, 1]:
                    vals = [str(r["waktu"]), str(r["barcode"]), str(r["nama_barang"]), str(r["kat"]), str(r["rk"]), str(r["sl"]), str(r["qty"]), str(r["ket"])]
                else:
                    vals = [str(r["waktu"] or "-"), str(r["barcode"]), str(r["nama_barang"]), str(r["kat"]), str(r["rk"]), str(r["sl"]), str(r["in_q"]), str(r["out_q"]), str(r["stok"])]
                
                for col, v in enumerate(vals):
                    item = QTableWidgetItem(v); item.setTextAlignment(Qt.AlignCenter); self.table.setItem(i, col, item)
            conn.close(); self.filter_tabel_internal()
        except Exception as e: print(f"Load Laporan Error: {e}")

    def load_analisis_pergerakan(self):
        """Implementasi Analisis Fast & Slow Moving."""
        try:
            conn = get_connection(); cursor = conn.cursor()
            
            # 1. AMBIL BARANG FAST MOVING (Banyak keluar dalam 30 hari terakhir)
            tgl_30 = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT b.barcode, b.nama_barang, COALESCE(k.nama_kategori, '-'), b.rak, COALESCE(l.nama_lokasi, '-'), b.stok, COUNT(t.id_transaksi) as total_trx
                FROM barang_baru b
                LEFT JOIN kategori k ON b.id_kategori = k.id_kategori
                LEFT JOIN lokasi l ON b.id_lokasi = l.id_lokasi
                JOIN transaksi t ON b.id_barang = t.id_barang
                WHERE t.jenis = 'KELUAR' AND t.tanggal >= ?
                GROUP BY b.id_barang
                HAVING total_trx >= 3
                ORDER BY total_trx DESC
            """, (tgl_30,))
            fast_moving = cursor.fetchall()
            
            # 2. AMBIL BARANG SLOW MOVING (Stok > 0 tapi tidak ada transaksi keluar dalam 180 hari)
            tgl_180 = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT b.barcode, b.nama_barang, COALESCE(k.nama_kategori, '-'), b.rak, COALESCE(l.nama_lokasi, '-'), b.stok
                FROM barang_baru b
                LEFT JOIN kategori k ON b.id_kategori = k.id_kategori
                LEFT JOIN lokasi l ON b.id_lokasi = l.id_lokasi
                WHERE b.stok > 0 AND b.id_barang NOT IN (
                    SELECT DISTINCT id_barang FROM transaksi 
                    WHERE jenis = 'KELUAR' AND tanggal >= ?
                )
            """, (tgl_180,))
            slow_moving = cursor.fetchall()
            
            self.table.setRowCount(0)
            
            # Masukkan Fast Moving
            from PySide6.QtGui import QColor, QFont
            for r in fast_moving:
                i = self.table.rowCount()
                self.table.insertRow(i)
                items = [str(r[0]), str(r[1]), str(r[2]), str(r[3]), str(r[4]), str(r[5]), "🔥 FAST MOVING", f"{r[6]}x Keluar (30 hari)"]
                for c, text in enumerate(items):
                    iti = QTableWidgetItem(text)
                    if c == 6: 
                        iti.setForeground(QColor("#059669"))
                        f = QFont(); f.setBold(True); iti.setFont(f)
                    self.table.setItem(i, c, iti)
            
            # Masukkan Slow Moving
            for r in slow_moving:
                i = self.table.rowCount()
                self.table.insertRow(i)
                items = [str(r[0]), str(r[1]), str(r[2]), str(r[3]), str(r[4]), str(r[5]), "❄️ SLOW MOVING", "> 180 hari tanpa keluar"]
                for c, text in enumerate(items):
                    iti = QTableWidgetItem(text)
                    if c == 6: 
                        iti.setForeground(QColor("#4b5563"))
                        f = QFont(); f.setBold(True); iti.setFont(f)
                    self.table.setItem(i, c, iti)
            
            self.card_masuk.count_label.setText(f"{len(fast_moving)} Item")
            self.card_masuk.total_label.setText("Kategori Cepat")
            self.card_keluar.count_label.setText(f"{len(slow_moving)} Item")
            self.card_keluar.total_label.setText("Kategori Lambat")
            
            conn.close()
        except Exception as e:
            print(f"Error Analisis: {e}")

    def filter_tabel_internal(self):
        kw = self.input_cari.text().lower()
        for r in range(self.table.rowCount()):
            kode = self.table.item(r, 1).text().lower()
            nama = self.table.item(r, 2).text().lower()
            lok = self.table.item(r, 4).text().lower()
            self.table.setRowHidden(r, not (kw in kode or kw in nama or kw in lok))

    def export_to_excel(self):
        if self.table.rowCount() == 0:
            self.show_notif("Peringatan", "Tabel laporan kosong. Tidak ada data untuk diekspor.", is_error=True); return
        
        jenis_text = self.filter_jenis.currentText().upper()
        path, _ = QFileDialog.getSaveFileName(self, "Simpan Excel", f"Laporan_{jenis_text}_PTPN4.xlsx", "Excel Files (*.xlsx)")
        if not path: return

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Laporan Inventaris"

            # 1. Judul Laporan (Header)
            ws.merge_cells("A1:H1")
            ws["A1"] = "PT PERKEBUNAN NUSANTARA IV KEBUN ADOLINA"
            ws["A1"].font = Font(size=16, bold=True, color="FFFFFF")
            ws["A1"].fill = PatternFill("solid", fgColor="0B5345")
            ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

            ws.merge_cells("A2:H2")
            ws["A2"] = f"Laporan {jenis_text} - Periode: {self.filter_periode.currentText()}"
            ws["A2"].font = Font(size=12, bold=True, color="FFFFFF")
            ws["A2"].fill = PatternFill("solid", fgColor="117A65")
            ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

            # 2. Header Tabel
            col_count = self.table.columnCount()
            headers = [self.table.horizontalHeaderItem(i).text() for i in range(col_count)]
            ws.append([]) # Empty Row
            ws.append(headers)

            header_row = 4
            thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
            
            for col, title in enumerate(headers, 1):
                cell = ws.cell(row=header_row, column=col)
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="34495E")
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = thin_border

            # 3. Data Tabel
            start_row_data = header_row + 1
            for r in range(self.table.rowCount()):
                if not self.table.isRowHidden(r):
                    row_data = [self.table.item(r, c).text() for c in range(col_count)]
                    ws.append(row_data)
                    
                    # Styling borders and alignment per cell
                    current_row = ws.max_row
                    for col in range(1, col_count + 1):
                        cell = ws.cell(row=current_row, column=col)
                        cell.border = thin_border
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                        
                        # Jika kolom numerik (Qty/Stok), paksa tipe ke integer jika bisa
                        if headers[col-1].lower() in ('qty masuk', 'qty keluar', 'sisa stok', 'masuk', 'keluar'):
                            try:
                                cell.value = int(cell.value)
                            except Exception as e: print(f"Remove Temp File Error: {e}")

            # 4. Auto-Fit Columns
            for col in range(1, col_count + 1):
                column_letter = openpyxl.utils.get_column_letter(col)
                ws.column_dimensions[column_letter].width = 15 # Default width
            ws.column_dimensions['A'].width = 18 # Tanggal
            ws.column_dimensions['C'].width = 30 # Nama Barang
            ws.column_dimensions['H'].width = 25 # Suplier/Penerima

            # 5. Tambahkan Grafik Chart Laporan (Khusus untuk Qty)
            max_r = ws.max_row
            if max_r > header_row and jenis_text != "RINGKASAN SEMUA":
                # Cari kolom target (Qty)
                qty_col_index = None
                for idx, h in enumerate(headers):
                    if h.lower() in ('qty masuk', 'qty keluar'):
                        qty_col_index = idx + 1
                        break
                
                if qty_col_index:
                    chart = BarChart()
                    chart.type = "col"
                    chart.style = 10
                    chart.title = f"Grafik {jenis_text}"
                    chart.y_axis.title = 'Jumlah (Unit)'
                    chart.x_axis.title = 'Nama Barang'

                    data = Reference(ws, min_col=qty_col_index, min_row=header_row, max_row=max_r)
                    cats = Reference(ws, min_col=3, min_row=start_row_data, max_row=max_r) # Asumsi Nama Barang selalu ada di Kolom ke 3(C)
                    
                    chart.add_data(data, titles_from_data=True)
                    chart.set_categories(cats)
                    chart.width = 18
                    chart.height = 10
                    
                    ws.add_chart(chart, f"A{max_r + 3}")

            wb.save(path)
            catat_log(f"Mengekspor laporan {jenis_text} ke format Microsoft Excel (XLSX).")
            self.show_notif("Sukses", f"Laporan Excel berhasil diekspor ke:\n{path}")
            
            if os.name == 'nt': os.startfile(path)

        except Exception as e: self.show_notif("Gagal", str(e), is_error=True)

    def export_to_pdf(self):
        if self.table.rowCount() == 0: return
        jenis_text = self.filter_jenis.currentText().upper()
        path, _ = QFileDialog.getSaveFileName(self, "Simpan PDF", f"Laporan_{jenis_text}_PTPN4.pdf", "PDF Files (*.pdf)")
        if not path: return

        try:
            doc = SimpleDocTemplate(path, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
            elements = []
            styles = getSampleStyleSheet()

            # --- KOP SURAT (PTPN IV KEBUN ADOLINA) ---
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            logo_path = os.path.join(base_path, "assets", "images", "Logo PTPN IV.png")
            title_s = ParagraphStyle('T1', fontSize=18, leading=22, fontName='Helvetica-Bold', alignment=1)
            unit_s = ParagraphStyle('T2', fontSize=16, leading=20, fontName='Helvetica-Bold', alignment=1)
            addr_s = ParagraphStyle('T3', fontSize=9, leading=11, alignment=1)
            
            header = [
                Paragraph("<b>PT PERKEBUNAN NUSANTARA IV</b>", title_s),
                Paragraph("<b>KEBUN ADOLINA</b>", unit_s),
                Paragraph("Jl. Medan - Tebing Tinggi, Batang Terap, Kec. Perbaungan,", addr_s),
                Paragraph("Kabupaten Serdang Bedagai, Sumatera Utara 20986", addr_s),
                Paragraph(f"<i>Tipe: LAPORAN {jenis_text} | Periode: {self.filter_periode.currentText()}</i>", addr_s)
            ]
            
            if os.path.exists(logo_path):
                img_logo = RLImage(logo_path, width=1.1*inch, height=1.1*inch)
                kop_table = Table([[img_logo, header]], colWidths=[1.5*inch, 8.5*inch])
            else:
                kop_table = Table([[header]], colWidths=[10*inch])
            
            kop_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (0,0), (-1,-1), 'CENTER')]))
            elements.append(kop_table)
            elements.append(HRFlowable(width="100%", thickness=2, color=colors.black, spaceBefore=5, spaceAfter=1))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.black, spaceBefore=1, spaceAfter=15))

            # --- TABEL DATA DINAMIS ---
            cell_h = ParagraphStyle('CH', fontSize=9, alignment=1, textColor=colors.whitesmoke, fontName='Helvetica-Bold')
            cell_b = ParagraphStyle('CB', fontSize=8, alignment=1, splitLongWords=False) 

            # Col widths based on current table cols
            col_count = self.table.columnCount()
            num_cols = list(range(col_count))
            
            if col_count == 8: # Masuk / Keluar
                col_w = [1.2*inch, 1.2*inch, 2.0*inch, 1.0*inch, 0.9*inch, 0.9*inch, 0.8*inch, 1.8*inch]
            else: # Ringkasan
                col_w = [1.2*inch, 1.1*inch, 1.8*inch, 0.9*inch, 0.9*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.9*inch]

            data = [[Paragraph(self.table.horizontalHeaderItem(i).text(), cell_h) for i in num_cols]]
            for r in range(self.table.rowCount()):
                if not self.table.isRowHidden(r):
                    data.append([Paragraph(self.table.item(r, i).text(), cell_b) for i in num_cols])

            t = Table(data, repeatRows=1, colWidths=col_w)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')), 
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), 
                ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6)
            ]))
            elements.append(t)

            if col_count == 9: # IF SEMUA
                elements.append(PageBreak())
                elements.append(Paragraph("<b>RINGKASAN STOK SAAT INI (PER LOKASI & KATEGORI)</b>", styles['Heading2']))
                elements.append(Spacer(1, 15))
                conn = get_connection(); cursor = conn.cursor()
                cursor.execute("SELECT k.nama_kategori, b.rak, l.nama_lokasi, SUM(b.stok) FROM barang_baru b JOIN kategori k ON b.id_kategori=k.id_kategori JOIN lokasi l ON b.id_lokasi=l.id_lokasi GROUP BY k.nama_kategori, b.rak, l.nama_lokasi ORDER BY k.nama_kategori")
                sum_data = [[Paragraph(x, cell_h) for x in ["KATEGORI", "RAK", "SLOT", "TOTAL STOK GUDANG"]]]
                for sr in cursor.fetchall(): sum_data.append([Paragraph(str(x), cell_b) for x in sr])
                conn.close()
                ts = Table(sum_data, colWidths=[3*inch, 2.5*inch, 2.5*inch, 2.5*inch])
                ts.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4b6584')), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('TOPPADDING', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,-1), 8)]))
                elements.append(ts)

            elements.append(Spacer(1, 50))
            ttd_data = [["", f"Perbaungan, {datetime.now().strftime('%d %B %Y')}"], ["", "Manajer Gudang Inventaris,"], ["", ""], ["", ""], ["", ""], ["", "__________________________"]]
            ttd_table = Table(ttd_data, colWidths=[8.0*inch, 2.5*inch])
            ttd_table.setStyle(TableStyle([('ALIGN', (1, 0), (1, -1), 'CENTER')])); elements.append(ttd_table)

            doc.build(elements); self.show_notif("Sukses", f"Laporan {jenis_text} berhasil dibuat.")
            if os.name == 'nt': os.startfile(path)
        except Exception as e: self.show_notif("Error", f"Gagal membuat PDF: {e}", is_error=True)