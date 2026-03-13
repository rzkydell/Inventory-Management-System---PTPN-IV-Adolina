import sqlite3
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QCheckBox, QAbstractItemView, QSizePolicy, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from database.connection import get_connection
from datetime import datetime, timedelta

# Library untuk Grafik
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class DashboardPage(QWidget):
    """
    Halaman Dashboard Utama PTPN IV.
    Seluruh filter (Grafik & Tabel) dibuat dengan kontras tinggi agar terlihat jelas.
    """
    def __init__(self):
        super().__init__()
        self.already_notified = set()
        self.init_ui()
        self.load_categories_filter()
        self.refresh_data()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_categories_filter()
        self.refresh_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_root = QScrollArea()
        self.scroll_root.setWidgetResizable(True)
        self.scroll_root.setStyleSheet("QScrollArea { border: none; background-color: #f8fafc; }")
        
        container = QWidget()
        container.setStyleSheet("background-color: #f8fafc;")
        self.content_layout = QVBoxLayout(container)
        self.content_layout.setContentsMargins(15, 15, 15, 15)
        self.content_layout.setSpacing(20)

        # --- KPI CARDS ---
        header_stats = QHBoxLayout()
        header_stats.setSpacing(15)
        self.card_total = self.create_kpi_card("TOTAL INVENTARIS", "0", "Jenis Barang Aktif", "#3b82f6")
        self.card_kritis = self.create_kpi_card("STOK KRITIS", "0", "Segera Re-stock", "#ef4444")
        self.card_masuk = self.create_kpi_card("MASUK HARI INI", "0", "Total Transaksi", "#10b981")
        self.card_keluar = self.create_kpi_card("KELUAR HARI INI", "0", "Total Transaksi", "#f59e0b")
        for c in [self.card_total, self.card_kritis, self.card_masuk, self.card_keluar]: header_stats.addWidget(c)
        self.content_layout.addLayout(header_stats)

        # --- MIDDLE SECTION: CHARTS ---
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(15)

        # 1. LINE CHART (TREND)
        self.line_card = QFrame()
        self.line_card.setMinimumHeight(350)
        self.line_card.setStyleSheet("background: white; border-radius: 16px; border: 1px solid #e2e8f0;")
        self.apply_shadow(self.line_card)
        line_vbox = QVBoxLayout(self.line_card)
        line_vbox.setContentsMargins(15, 15, 15, 15)
        
        line_header = QHBoxLayout()
        lbl_trend = QLabel("📈 Tren Aktivitas")
        lbl_trend.setStyleSheet("font-weight: 800; color: #1e293b; font-size: 13px;")
        line_header.addWidget(lbl_trend)
        line_header.addStretch()
        
        # STYLING CHECKBOX AGAR TERLIHAT JELAS (HITAM)
        checkbox_style = """
            QCheckBox { 
                color: #1e293b; 
                font-weight: bold; 
                font-size: 11px; 
                spacing: 5px;
            }
            QCheckBox::indicator { width: 16px; height: 16px; }
        """
        self.filter_line_in = QCheckBox("Masuk")
        self.filter_line_in.setChecked(True)
        self.filter_line_in.setStyleSheet(checkbox_style)
        
        self.filter_line_out = QCheckBox("Keluar")
        self.filter_line_out.setChecked(True)
        self.filter_line_out.setStyleSheet(checkbox_style)
        
        line_header.addWidget(self.filter_line_in)
        line_header.addWidget(self.filter_line_out)
        line_vbox.addLayout(line_header)
        
        self.fig_line = Figure(figsize=(5, 3), dpi=100); self.canvas_line = FigureCanvas(self.fig_line)
        line_vbox.addWidget(self.canvas_line); middle_layout.addWidget(self.line_card, 3)

        # 2. DONUT CHART
        self.donut_card = QFrame()
        self.donut_card.setMinimumHeight(350)
        self.donut_card.setStyleSheet("background: white; border-radius: 16px; border: 1px solid #e2e8f0;")
        self.apply_shadow(self.donut_card)
        donut_vbox = QVBoxLayout(self.donut_card)
        lbl_dist = QLabel("🍩 Distribusi Stok")
        lbl_dist.setStyleSheet("font-weight: 800; color: #1e293b; font-size: 13px;")
        donut_vbox.addWidget(lbl_dist)
        
        self.fig_donut = Figure(figsize=(3, 3), dpi=100); self.canvas_donut = FigureCanvas(self.fig_donut)
        donut_vbox.addWidget(self.canvas_donut); middle_layout.addWidget(self.donut_card, 2)

        self.content_layout.addLayout(middle_layout)

        # --- NEW SECTION: ANALYTICS 2.0 (PIE CHARTS) ---
        analytics_layout = QHBoxLayout()
        analytics_layout.setSpacing(15)

        # 3. CATEGORY PIE CHART
        self.cat_card = QFrame()
        self.cat_card.setMinimumHeight(350)
        self.cat_card.setStyleSheet("background: white; border-radius: 16px; border: 1px solid #e2e8f0;")
        self.apply_shadow(self.cat_card)
        cat_vbox = QVBoxLayout(self.cat_card)
        lbl_cat = QLabel("📊 Distribusi per Kategori")
        lbl_cat.setStyleSheet("font-weight: 800; color: #1e293b; font-size: 13px;")
        cat_vbox.addWidget(lbl_cat)
        self.fig_cat = Figure(figsize=(3, 3), dpi=100); self.canvas_cat = FigureCanvas(self.fig_cat)
        cat_vbox.addWidget(self.canvas_cat); analytics_layout.addWidget(self.cat_card, 1)

        # 4. RAK PIE CHART
        self.loc_card = QFrame()
        self.loc_card.setMinimumHeight(350)
        self.loc_card.setStyleSheet("background: white; border-radius: 16px; border: 1px solid #e2e8f0;")
        self.apply_shadow(self.loc_card)
        loc_vbox = QVBoxLayout(self.loc_card)
        lbl_loc = QLabel("📍 Distribusi per RAK")
        lbl_loc.setStyleSheet("font-weight: 800; color: #1e293b; font-size: 13px;")
        loc_vbox.addWidget(lbl_loc)
        self.fig_loc = Figure(figsize=(3, 3), dpi=100); self.canvas_loc = FigureCanvas(self.fig_loc)
        loc_vbox.addWidget(self.canvas_loc); analytics_layout.addWidget(self.loc_card, 1)

        self.content_layout.addLayout(analytics_layout)

        # --- BOTTOM: MONITOR TABLE WITH FILTER ---
        monitor_frame = QFrame()
        monitor_frame.setStyleSheet("background: white; border-radius: 16px; border: 1px solid #e2e8f0;")
        self.apply_shadow(monitor_frame)
        monitor_layout = QVBoxLayout(monitor_frame)
        monitor_layout.setContentsMargins(20, 20, 20, 20)
        
        monitor_header = QHBoxLayout()
        lbl_monitor = QLabel("🚨 MONITOR STOK KRITIS (<= STOK MIN)")
        lbl_monitor.setStyleSheet("font-size: 14px; font-weight: 800; color: #b91c1c;")
        monitor_header.addWidget(lbl_monitor)
        monitor_header.addStretch()
        
        lbl_f_text = QLabel("Pilih Kategori:")
        lbl_f_text.setStyleSheet("font-size: 12px; color: #1e293b; font-weight: bold;")
        monitor_header.addWidget(lbl_f_text)

        self.combo_filter_kritis = QComboBox()
        self.combo_filter_kritis.setFixedWidth(200)
        self.combo_filter_kritis.setStyleSheet("""
            QComboBox { 
                background-color: #ffffff; border: 2px solid #cbd5e1; 
                border-radius: 6px; padding: 5px; color: #000000; font-weight: 600;
            }
            QComboBox QAbstractItemView { background-color: #ffffff; color: #000000; selection-background-color: #3b82f6; }
        """)
        self.combo_filter_kritis.currentIndexChanged.connect(self.refresh_monitor_table)
        monitor_header.addWidget(self.combo_filter_kritis)
        monitor_layout.addLayout(monitor_header)
        
        self.table_kritis = QTableWidget()
        self.table_kritis.setColumnCount(6)
        self.table_kritis.setHorizontalHeaderLabels(["Barcode", "Nama Barang", "Kategori", "RAK", "Slot", "Sisa Stok"])
        self.table_kritis.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_kritis.verticalHeader().setVisible(False)
        self.table_kritis.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_kritis.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_kritis.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_kritis.setStyleSheet("""
            QTableWidget { border: none; color: #1e293b; background-color: transparent; } 
            QHeaderView::section { background: #f8fafc; color: #475569; font-weight: bold; border-bottom: 2px solid #e2e8f0; padding: 12px; }
        """)
        monitor_layout.addWidget(self.table_kritis)
        self.content_layout.addWidget(monitor_frame)

        # --- BOTTOM 2: AI PREDICTION WARNING TABLE ---
        prediksi_frame = QFrame()
        prediksi_frame.setStyleSheet("background: white; border-radius: 16px; border: 1px solid #e2e8f0;")
        self.apply_shadow(prediksi_frame)
        prediksi_layout = QVBoxLayout(prediksi_frame)
        prediksi_layout.setContentsMargins(20, 20, 20, 20)
        
        lbl_prediksi = QLabel("🧠 ANALISIS AI: PREDIKSI BARANG AKAN HABIS DALAM < 7 HARI")
        lbl_prediksi.setStyleSheet("font-size: 14px; font-weight: 800; color: #f59e0b;") # Orange color
        prediksi_layout.addWidget(lbl_prediksi)
        
        self.table_prediksi = QTableWidget()
        self.table_prediksi.setColumnCount(4)
        self.table_prediksi.setHorizontalHeaderLabels(["Nama Barang", "Rata-Guna /Hari", "Stok Tersisa", "🔥 Perkiraan Habis (Hari)"])
        self.table_prediksi.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_prediksi.verticalHeader().setVisible(False)
        self.table_prediksi.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_prediksi.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_prediksi.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_prediksi.setStyleSheet("""
            QTableWidget { border: none; color: #1e293b; background-color: transparent; } 
            QHeaderView::section { background: #f8fafc; color: #475569; font-weight: bold; border-bottom: 2px solid #e2e8f0; padding: 12px; }
            QTableWidget::item { padding: 5px; }
        """)
        prediksi_layout.addWidget(self.table_prediksi)
        self.content_layout.addWidget(prediksi_frame)

        self.content_layout.addStretch()

        # Connect Events
        self.filter_line_in.stateChanged.connect(self.refresh_data)
        self.filter_line_out.stateChanged.connect(self.refresh_data)

        self.scroll_root.setWidget(container)
        main_layout.addWidget(self.scroll_root)

    def load_categories_filter(self):
        try:
            current = self.combo_filter_kritis.currentText()
            self.combo_filter_kritis.blockSignals(True)
            self.combo_filter_kritis.clear()
            self.combo_filter_kritis.addItem("Semua Kategori")
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("SELECT nama_kategori FROM kategori ORDER BY nama_kategori ASC")
            for r in cursor.fetchall(): self.combo_filter_kritis.addItem(r[0])
            conn.close()
            if current: self.combo_filter_kritis.setCurrentText(current)
            self.combo_filter_kritis.blockSignals(False)
        except: pass

    def adjust_table_height(self):
        h_height = self.table_kritis.horizontalHeader().height()
        row_c = self.table_kritis.rowCount()
        new_h = h_height + (max(row_c, 1) * 45) + 20
        self.table_kritis.setFixedHeight(new_h)
        
        h_height_p = self.table_prediksi.horizontalHeader().height()
        row_c_p = self.table_prediksi.rowCount()
        new_h_p = h_height_p + (max(row_c_p, 1) * 35) + 20
        self.table_prediksi.setFixedHeight(new_h_p)

    def create_kpi_card(self, title, value, subtext, color):
        card = QFrame()
        card.setStyleSheet("background: white; border-radius: 16px; border: 1px solid #e2e8f0;")
        self.apply_shadow(card)
        l = QVBoxLayout(card); l.setContentsMargins(20, 20, 20, 20)
        lbl_t = QLabel(title); lbl_t.setStyleSheet("font-size: 13px; color: #64748b; font-weight: 700;")
        lbl_v = QLabel(value); lbl_v.setStyleSheet(f"font-size: 32px; font-weight: 800; color: {color}; margin-top: 5px; margin-bottom: 5px;")
        lbl_s = QLabel(subtext); lbl_s.setStyleSheet("font-size: 12px; color: #94a3b8;")
        l.addWidget(lbl_t); l.addWidget(lbl_v); l.addWidget(lbl_s); card.val_label = lbl_v; return card

    def apply_shadow(self, widget):
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 20))
        widget.setGraphicsEffect(shadow)

    def update_charts(self, dates, data_in, data_out):
        self.fig_line.clear(); ax_line = self.fig_line.add_subplot(111)
        if self.filter_line_in.isChecked():
            ax_line.plot(dates, data_in, label='Masuk', color='#10b981', linewidth=3, marker='o', markersize=5)
            ax_line.fill_between(dates, data_in, color='#10b981', alpha=0.1)
        if self.filter_line_out.isChecked():
            ax_line.plot(dates, data_out, label='Keluar', color='#f59e0b', linewidth=3, marker='o', markersize=5)
            ax_line.fill_between(dates, data_out, color='#f59e0b', alpha=0.1)
        ax_line.legend(frameon=False, fontsize=9); ax_line.spines[['top','right']].set_visible(False)
        ax_line.tick_params(colors='#475569', labelsize=8); ax_line.grid(axis='y', linestyle='--', alpha=0.3)
        self.fig_line.tight_layout(); self.canvas_line.draw()

        self.fig_donut.clear(); ax_donut = self.fig_donut.add_subplot(111)
        pie_data, pie_labels, pie_colors = [], [], []
        if sum(data_in) > 0: pie_data.append(sum(data_in)); pie_labels.append('Total Masuk'); pie_colors.append('#10b981')
        if sum(data_out) > 0: pie_data.append(sum(data_out)); pie_labels.append('Total Keluar'); pie_colors.append('#f59e0b')
        if not pie_data:
            ax_donut.text(0.5, 0.5, "No Data", ha='center', va='center', color="#94a3b8")
        else:
            wedges, texts, autotexts = ax_donut.pie(pie_data, colors=pie_colors, autopct='%1.1f%%', startangle=90, wedgeprops={'width': 0.45, 'edgecolor':'w'}, pctdistance=0.75)
            for autotext in autotexts: autotext.set_color('#1e293b'); autotext.set_weight('bold'); autotext.set_size(9)
            ax_donut.legend(wedges, pie_labels, title="Keterangan:", loc="lower center", bbox_to_anchor=(0.5, -0.15), frameon=False, fontsize=8, ncol=2)
        self.fig_donut.tight_layout(); self.canvas_donut.draw()

    def refresh_data(self):
        try:
            conn = get_connection(); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
            h_ini = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("SELECT COUNT(*) as t FROM barang_baru"); self.card_total.val_label.setText(str(cursor.fetchone()['t']))
            cursor.execute("SELECT COUNT(*) as t FROM barang_baru WHERE stok <= stok_minimum"); self.card_kritis.val_label.setText(str(cursor.fetchone()['t']))
            cursor.execute("SELECT COUNT(*) as t FROM transaksi WHERE jenis='MASUK' AND tanggal LIKE ?", (f'{h_ini}%',)); self.card_masuk.val_label.setText(str(cursor.fetchone()['t']))
            cursor.execute("SELECT COUNT(*) as t FROM transaksi WHERE jenis='KELUAR' AND tanggal LIKE ?", (f'{h_ini}%',)); self.card_keluar.val_label.setText(str(cursor.fetchone()['t']))
            
            dates, data_in, data_out = [], [], []
            for i in range(6, -1, -1):
                t = (datetime.now() - timedelta(days=i))
                dates.append(t.strftime('%d %b'))
                cursor.execute("SELECT COUNT(*) as c FROM transaksi WHERE jenis='MASUK' AND tanggal LIKE ?", (f"{t.strftime('%Y-%m-%d')}%",))
                data_in.append(cursor.fetchone()['c'])
                cursor.execute("SELECT COUNT(*) as c FROM transaksi WHERE jenis='KELUAR' AND tanggal LIKE ?", (f"{t.strftime('%Y-%m-%d')}%",))
                data_out.append(cursor.fetchone()['c'])
            self.update_charts(dates, data_in, data_out)
            conn.close()
            self.refresh_monitor_table()
            self.refresh_prediksi_table()
            self.refresh_analytics()
        except Exception as e: print(f"Dashboard Refresh Error: {e}")

    def refresh_analytics(self):
        try:
            conn = get_connection(); cursor = conn.cursor()
            
            # --- PIE KATEGORI ---
            cursor.execute("""
                SELECT k.nama_kategori, SUM(b.stok) 
                FROM barang_baru b 
                JOIN kategori k ON b.id_kategori = k.id_kategori 
                GROUP BY k.id_kategori
            """)
            cat_data = cursor.fetchall()
            self.fig_cat.clear(); ax_cat = self.fig_cat.add_subplot(111)
            
            if not cat_data:
                ax_cat.text(0.5, 0.5, "No Category Data", ha='center', va='center', color="#94a3b8")
            else:
                vals = [r[1] for r in cat_data if r[1] > 0]
                labels = [r[0] for r in cat_data if r[1] > 0]
                if vals:
                    ax_cat.pie(vals, labels=labels, autopct='%1.1f%%', startangle=140, 
                               colors=['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'],
                               textprops={'fontsize': 8, 'color': '#111827', 'weight': 'bold'})
                else:
                    ax_cat.text(0.5, 0.5, "Stock Empty", ha='center', va='center', color="#94a3b8")
            self.fig_cat.tight_layout(); self.canvas_cat.draw()

            # --- PIE RAK ---
            cursor.execute("""
                SELECT rak, SUM(stok) 
                FROM barang_baru 
                GROUP BY rak
            """)
            rak_data = cursor.fetchall()
            self.fig_loc.clear(); ax_loc = self.fig_loc.add_subplot(111)
            
            if not rak_data:
                ax_loc.text(0.5, 0.5, "No Rak Data", ha='center', va='center', color="#94a3b8")
            else:
                vals = [r[1] for r in rak_data if r[1] > 0]
                labels = [r[0] if r[0] else "Tanpa Rak" for r in rak_data if r[1] > 0]
                if vals:
                    ax_loc.pie(vals, labels=labels, autopct='%1.1f%%', startangle=140, 
                               colors=['#6366f1', '#14b8a6', '#f97316', '#d946ef', '#ec4899', '#84cc16'],
                               textprops={'fontsize': 8, 'color': '#111827', 'weight': 'bold'})
                else:
                    ax_loc.text(0.5, 0.5, "Stock Empty", ha='center', va='center', color="#94a3b8")
            self.fig_loc.tight_layout(); self.canvas_loc.draw()

            conn.close()
        except Exception as e: print(f"Analytics Error: {e}")

    def refresh_monitor_table(self):
        try:
            f_val = self.combo_filter_kritis.currentText()
            conn = get_connection(); cursor = conn.cursor()
            query = "SELECT b.barcode, b.nama_barang, COALESCE(k.nama_kategori, '-'), b.rak, COALESCE(l.nama_lokasi, '-'), b.stok FROM barang_baru b LEFT JOIN kategori k ON b.id_kategori = k.id_kategori LEFT JOIN lokasi l ON b.id_lokasi = l.id_lokasi WHERE b.stok <= b.stok_minimum"
            params = []
            if f_val and f_val != "Semua Kategori":
                query += " AND k.nama_kategori = ?"; params.append(f_val)
            query += " ORDER BY b.stok ASC LIMIT 20"
            cursor.execute(query, params); rows = cursor.fetchall(); self.table_kritis.setRowCount(0)
            
            # Tray Notification Integration
            from PySide6.QtWidgets import QSystemTrayIcon
            for r in rows:
                barcode = r[0]
                if barcode not in self.already_notified:
                    self.already_notified.add(barcode)
                    main_win = self.window()
                    if hasattr(main_win, 'send_tray_notification'):
                        main_win.send_tray_notification(
                            "⚠️ Stok Kritis Terdeteksi",
                            f"{r[1]} tersisa {r[5]}. Segera restock!",
                            QSystemTrayIcon.Warning
                        )

            for i, r in enumerate(rows):
                self.table_kritis.insertRow(i)
                for c in range(6):
                    v = f"⚠️ {r[c]}" if c == 5 else str(r[c])
                    item = QTableWidgetItem(v)
                    item.setForeground(QColor("#b91c1c" if c == 5 else "#1e293b"))
                    if c == 5: item.setTextAlignment(Qt.AlignCenter); item.setFont(QFont("Segoe UI", weight=QFont.Bold))
                    self.table_kritis.setItem(i, c, item)
            self.adjust_table_height(); conn.close()
        except Exception as e: print(f"Table Error: {e}")

    def refresh_prediksi_table(self):
        try:
            conn = get_connection(); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
            date_30_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            # Ambil semua transaksi KELUAR 30 hari terakhir
            query = """
                SELECT t.id_barang, b.nama_barang, b.stok, t.tanggal, t.stok_sebelum, t.stok_sesudah 
                FROM transaksi t
                JOIN barang_baru b ON t.id_barang = b.id_barang
                WHERE t.jenis = 'KELUAR' AND t.tanggal >= ?
                ORDER BY t.tanggal ASC
            """
            cursor.execute(query, (date_30_days_ago,))
            rows = cursor.fetchall()
            
            # Kelompokkan histori per barang
            history_per_item = {}
            for r in rows:
                item_id = r['id_barang']
                if item_id not in history_per_item:
                    history_per_item[item_id] = {
                        'nama': r['nama_barang'],
                        'sisa_stok': r['stok'],
                        'data_x_hari': [],
                        'data_y_qty': [],
                        'cumulative_out': 0
                    }
                
                # Hitung selisih qty keluar
                qty_keluar = abs(r['stok_sebelum'] - r['stok_sesudah'])
                history_per_item[item_id]['cumulative_out'] += qty_keluar
                
                # Parsing hari ke-berapa sejak 30 hari lalu (sebagai X)
                tgl_transaksi = datetime.strptime(r['tanggal'][:10], '%Y-%m-%d')
                delta_hari = (tgl_transaksi - datetime.now() + timedelta(days=30)).days
                
                history_per_item[item_id]['data_x_hari'].append(delta_hari)
                history_per_item[item_id]['data_y_qty'].append(history_per_item[item_id]['cumulative_out'])

            bahaya_list = []
            
            # --- LOGIKA REGRESI LINIER (y = mx + c) ---
            for item_id, data in history_per_item.items():
                xs = data['data_x_hari']
                ys = data['data_y_qty']
                n = len(xs)
                current_stock = data['sisa_stok']
                
                # Butuh minimal 2 titik data untuk regresi yang punya arti
                if n < 2 or current_stock <= 0:
                    continue
                    
                sum_x = sum(xs)
                sum_y = sum(ys)
                sum_x_sq = sum([x**2 for x in xs])
                sum_xy = sum([xs[i] * ys[i] for i in range(n)])
                
                denominator = (n * sum_x_sq - sum_x**2)
                if denominator == 0:
                    continue # Menghindari division by zero jika semua transaksi di hari yang sama
                    
                # Menghitung Gradien (m/slope) yaitu Rata-rata percepatan keluarnya barang per hari
                slope = (n * sum_xy - sum_x * sum_y) / denominator
                
                # Jika slope <= 0 artinya tidak ada tren/barang tidak keluar lagi (stagnan)
                if slope > 0:
                    # Rumus Sisa Hari = Sisa Stok / Slope (Kecepatan Tren)
                    estimasi_hari_habis = current_stock / slope
                    
                    # Tampilkan yang prediksi habis di bawah 7 hari
                    if estimasi_hari_habis < 7.0:
                        bahaya_list.append((data['nama'], slope, current_stock, int(estimasi_hari_habis)))
            
            bahaya_list.sort(key=lambda x: x[3]) # Sortir by remaining days
            
            self.table_prediksi.setRowCount(0)
            if not bahaya_list:
                self.table_prediksi.insertRow(0)
                item = QTableWidgetItem("Aman (Sistem Regresi Linier tidak menemukan potensi stok habis < 7 hari)")
                item.setTextAlignment(Qt.AlignCenter)
                self.table_prediksi.setItem(0, 0, item)
                self.table_prediksi.setSpan(0, 0, 1, 4)
            else:
                for i, r in enumerate(bahaya_list):
                    self.table_prediksi.insertRow(i)
                    self.table_prediksi.setItem(i, 0, QTableWidgetItem(r[0]))
                    item_rata = QTableWidgetItem(f"Tren: {r[1]:.1f} / hari")
                    item_rata.setTextAlignment(Qt.AlignCenter)
                    self.table_prediksi.setItem(i, 1, item_rata)
                    item_stok = QTableWidgetItem(str(r[2]))
                    item_stok.setTextAlignment(Qt.AlignCenter)
                    self.table_prediksi.setItem(i, 2, item_stok)
                    
                    item_hari = QTableWidgetItem(f"{r[3]} Hari Lagi")
                    item_hari.setTextAlignment(Qt.AlignCenter)
                    item_hari.setForeground(QColor("#ef4444"))
                    font = QFont(); font.setBold(True); item_hari.setFont(font)
                    self.table_prediksi.setItem(i, 3, item_hari)
                    
            self.adjust_table_height(); conn.close()
        except Exception as e: print(f"Prediksi ML Error: {e}")