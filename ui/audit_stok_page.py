import os
import sqlite3
import cv2
import winsound
from pyzbar import pyzbar
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, 
    QTableWidgetItem, QMessageBox, QHeaderView,
    QFrame, QAbstractItemView, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from database.connection import get_connection, catat_log
from datetime import datetime

class AuditStokPage(QWidget):
    """
    Halaman Asisten Audit Stok (Opname Mandiri).
    Memungkinkan pengecekan stok fisik vs sistem secara cepat.
    """
    def __init__(self):
        super().__init__()
        self.audit_data = {} # {id_barang: {'nama': str, 'sistem': int, 'fisik': int}}
        self.init_ui()

    def init_ui(self):
        # Base background
        self.setStyleSheet("background-color: #f8fafc;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)

        # --- HEADER SECTION ---
        header_widget = QWidget()
        h_layout = QVBoxLayout(header_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(5)
        
        title = QLabel("MODUL AUDIT STOK (OPNAME)")
        title.setStyleSheet("color: #000000; font-size: 24px; font-weight: 800; border: none;")
        subtitle = QLabel("Lakukan verifikasi stok fisik gudang secara real-time.")
        subtitle.setStyleSheet("color: #000000; font-size: 13px; border: none;")
        h_layout.addWidget(title)
        h_layout.addWidget(subtitle)
        layout.addWidget(header_widget)

        # --- TOP CONTROL BAR ---
        control_card = QFrame()
        control_card.setStyleSheet("""
            QFrame { background-color: white; border-radius: 16px; border: 1px solid #e2e8f0; }
            QLabel { color: #000000; font-weight: bold; font-size: 12px; text-transform: uppercase; border: none; }
            QLineEdit { 
                background-color: #ffffff; 
                border: 2px solid #3b82f6; 
                border-radius: 10px; 
                padding: 12px 15px; 
                color: #000000; 
                font-size: 15px;
                font-weight: bold;
            }
        """)
        self.apply_shadow(control_card)
        control_layout = QHBoxLayout(control_card)
        control_layout.setContentsMargins(25, 25, 25, 25)
        control_layout.setSpacing(15)

        scan_container = QWidget()
        scan_v = QVBoxLayout(scan_container)
        scan_v.setContentsMargins(0, 0, 0, 0); scan_v.setSpacing(8)
        scan_v.addWidget(QLabel("INPUT SCAN / BARCODE"))
        self.input_scan = QLineEdit()
        self.input_scan.setPlaceholderText("Scan atau ketik barcode...")
        self.input_scan.returnPressed.connect(self.proses_audit_manual)
        scan_v.addWidget(self.input_scan)

        btn_scan = QPushButton("📷 KAMERA")
        btn_scan.setCursor(Qt.PointingHandCursor)
        btn_scan.setStyleSheet("""
            QPushButton { background-color: #3b82f6; color: white; padding: 15px 25px; font-weight: bold; border-radius: 10px; border: none; margin-top: 20px; }
            QPushButton:hover { background-color: #2563eb; }
        """)
        btn_scan.clicked.connect(self.scan_kamera_audit)

        self.btn_reset_audit = QPushButton("🔄 RESET")
        self.btn_reset_audit.setCursor(Qt.PointingHandCursor)
        self.btn_reset_audit.setStyleSheet("""
            QPushButton { background-color: #ef4444; color: white; padding: 15px 25px; font-weight: bold; border-radius: 10px; border: none; margin-top: 20px; }
            QPushButton:hover { background-color: #dc2626; }
        """)
        self.btn_reset_audit.clicked.connect(self.reset_audit)

        control_layout.addWidget(scan_container, 4)
        control_layout.addWidget(btn_scan, 1)
        control_layout.addWidget(self.btn_reset_audit, 1)
        layout.addWidget(control_card)

        # --- TABLE AUDIT ---
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["No", "Barcode", "Nama Barang", "Lokasi", "Sistem", "Fisik", "Selisih"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed); self.table.setColumnWidth(0, 50)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget { background: white; border-radius: 20px; border: 1px solid #e2e8f0; gridline-color: #f1f5f9; outline: none; }
            QHeaderView::section { background: #f8fafc; color: #000000; font-weight: 800; font-size: 11px; text-transform: uppercase; border: none; border-bottom: 2px solid #e2e8f0; padding: 15px; }
            QTableWidget::item { padding: 12px; color: #000000; border-bottom: 1px solid #f1f5f9; }
        """)
        self.apply_shadow(self.table)
        layout.addWidget(self.table)

        # --- BOTTOM ACTION BAR ---
        action_layout = QHBoxLayout()
        action_layout.setSpacing(15)
        
        self.btn_export = QPushButton("📊 CETAK LAPORAN AUDIT")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setStyleSheet("""
            QPushButton { background-color: #1e293b; color: white; padding: 18px; font-weight: bold; border-radius: 12px; border: none; }
            QPushButton:hover { background-color: #0f172a; }
        """)
        self.btn_export.clicked.connect(self.export_audit_pdf)
        
        self.btn_finalisasi = QPushButton("✅ FINALISASI & UPDATE STOK SISTEM")
        self.btn_finalisasi.setCursor(Qt.PointingHandCursor)
        self.btn_finalisasi.setStyleSheet("""
            QPushButton { background-color: #10b981; color: white; padding: 18px; font-weight: 900; font-size: 15px; border-radius: 12px; border: none; }
            QPushButton:hover { background-color: #059669; }
        """)
        self.btn_finalisasi.clicked.connect(self.finalisasi_audit)

        action_layout.addWidget(self.btn_export, 2)
        action_layout.addWidget(self.btn_finalisasi, 3)
        layout.addLayout(action_layout)

    def apply_shadow(self, widget):
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(20); shadow.setXOffset(0); shadow.setYOffset(4); shadow.setColor(QColor(0, 0, 0, 20))
        widget.setGraphicsEffect(shadow)

    def scan_kamera_audit(self):
        cap = cv2.VideoCapture(0)
        barcode_data = None
        while True:
            ret, frame = cap.read()
            if not ret: break
            for obj in pyzbar.decode(frame):
                barcode_data = obj.data.decode('utf-8'); break
            cv2.imshow("AUDIT SCANNER (ESC: Keluar)", frame)
            if barcode_data or cv2.waitKey(1) & 0xFF == 27: break
        cap.release(); cv2.destroyAllWindows()
        if barcode_data:
            winsound.Beep(1000, 200)
            self.tambah_ke_audit(barcode_data)

    def proses_audit_manual(self):
        bc = self.input_scan.text().strip()
        if bc:
            self.tambah_ke_audit(bc)
            self.input_scan.clear()

    def tambah_ke_audit(self, barcode):
        try:
            conn = get_connection(); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
            cursor.execute("""
                SELECT b.id_barang, b.nama_barang, b.stok, l.nama_lokasi 
                FROM barang_baru b 
                LEFT JOIN lokasi l ON b.id_lokasi = l.id_lokasi
                WHERE b.barcode = ?
            """, (barcode,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                return QMessageBox.warning(self, "Tidak Ditemukan", f"Barang dengan barcode {barcode} tidak ada di database.")

            id_b = row['id_barang']
            if id_b in self.audit_data:
                self.audit_data[id_b]['fisik'] += 1
            else:
                self.audit_data[id_b] = {
                    'barcode': barcode,
                    'nama': row['nama_barang'],
                    'lokasi': row['nama_lokasi'] or "-",
                    'sistem': row['stok'],
                    'fisik': 1
                }
            self.refresh_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def refresh_table(self):
        self.table.setRowCount(0)
        for i, (id_b, data) in enumerate(self.audit_data.items()):
            self.table.insertRow(i)
            selisih = data['fisik'] - data['sistem']
            
            self.table.setItem(i, 0, QTableWidgetItem(str(i+1)))
            self.table.setItem(i, 1, QTableWidgetItem(data['barcode']))
            self.table.setItem(i, 2, QTableWidgetItem(data['nama']))
            self.table.setItem(i, 3, QTableWidgetItem(data['lokasi']))
            self.table.setItem(i, 4, QTableWidgetItem(str(data['sistem'])))
            self.table.setItem(i, 5, QTableWidgetItem(str(data['fisik'])))
            
            si = QTableWidgetItem(str(selisih))
            font = QFont(); font.setBold(True); si.setFont(font)
            if selisih < 0: si.setForeground(QColor("#ef4444"))
            elif selisih > 0: si.setForeground(QColor("#3b82f6"))
            else: si.setForeground(QColor("#10b981"))
            self.table.setItem(i, 6, si)

    def reset_audit(self):
        if QMessageBox.question(self, "Reset", "Hapus data audit saat ini?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.audit_data = {}
            self.refresh_table()

    def finalisasi_audit(self):
        if not self.audit_data: return
        count = len(self.audit_data)
        if QMessageBox.question(self, "Konfirmasi", f"Update stok sistem untuk {count} barang ini sesuai hasil audit fisik?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                conn = get_connection(); cursor = conn.cursor()
                w_skrg = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                for id_b, data in self.audit_data.items():
                    if data['sistem'] != data['fisik']:
                        cursor.execute("UPDATE barang_baru SET stok = ? WHERE id_barang = ?", (data['fisik'], id_b))
                        # Catat transaksi penyesuaian
                        jenis = 'MASUK' if data['fisik'] > data['sistem'] else 'KELUAR'
                        cursor.execute("""
                            INSERT INTO transaksi (id_barang, jenis, stok_sebelum, stok_sesudah, metode, tanggal, keterangan)
                            VALUES (?, ?, ?, ?, 'AUDIT', ?, ?)
                        """, (id_b, jenis, data['sistem'], data['fisik'], w_skrg, "PENYESUAIAN STOK OPNAME"))
                conn.commit(); conn.close()
                catat_log(f"Finalisasi Audit Stok: {count} item diproses.")
                QMessageBox.information(self, "Selesai", "Stok sistem telah diperbarui sesuai data fisik.")
                self.audit_data = {}
                self.refresh_table()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal update: {e}")

    def export_audit_pdf(self):
        if not self.audit_data: return
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors

        path, _ = QFileDialog.getSaveFileName(self, "Simpan Laporan Audit", f"Audit_{datetime.now().strftime('%Y%m%d')}.pdf", "PDF Files (*.pdf)")
        if not path: return

        try:
            doc = SimpleDocTemplate(path, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            elements.append(Paragraph(f"<b>LAPORAN STOK OPNAME (AUDIT FISIK)</b>", styles['Title']))
            elements.append(Paragraph(f"Tanggal: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
            elements.append(Spacer(1, 20))

            data = [["No", "Barcode", "Nama Barang", "Lokasi", "Sist", "Fisk", "Sel"]]
            for i, (id_b, d) in enumerate(self.audit_data.items()):
                sel = d['fisik'] - d['sistem']
                data.append([str(i+1), d['barcode'], d['nama'], d['lokasi'], str(d['sistem']), str(d['fisik']), str(sel)])

            t = Table(data, colWidths=[30, 80, 160, 80, 40, 40, 40])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.addWidget(t)
            doc.build(elements)
            QMessageBox.information(self, "Berhasil", "Laporan audit berhasil diekspor.")
            os.startfile(path)
        except Exception as e:
            QMessageBox.critical(self, "Gagal", f"Error Export: {e}")
