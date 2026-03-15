import sqlite3
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QCheckBox, QAbstractItemView, QSizePolicy, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from models.barang_model import BarangModel
from models.transaksi_model import TransaksiModel
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
        
        # Dropdown Timeframe
        self.combo_timeframe = QComboBox()
        self.combo_timeframe.addItems(["7 Hari Terakhir", "30 Hari Terakhir", "1 Tahun Terakhir"])
        self.combo_timeframe.setStyleSheet("""
            QComboBox { background-color: #f8fafc; color: #1e293b; font-weight: bold; font-size: 11px; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px 10px; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: white;
                color: #1e293b;
                selection-background-color: #f1f5f9;
                selection-color: #3b82f6;
                outline: none;
                border: 1px solid #cbd5e1;
            }
        """)
        line_header.addWidget(self.combo_timeframe)
        
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
        self.combo_timeframe.currentIndexChanged.connect(self.refresh_data)

        self.scroll_root.setWidget(container)
        main_layout.addWidget(self.scroll_root)

    def load_categories_filter(self):
        try:
            from models.pendukung_model import PendukungModel
            current = self.combo_filter_kritis.currentText()
            self.combo_filter_kritis.blockSignals(True)
            self.combo_filter_kritis.clear()
            self.combo_filter_kritis.addItem("Semua Kategori")
            rows = PendukungModel.get_all_kategori()
            for r in rows: self.combo_filter_kritis.addItem(r[1])
            if current: self.combo_filter_kritis.setCurrentText(current)
            self.combo_filter_kritis.blockSignals(False)
        except Exception as e: print(f"Load Dashboard Error: {e}")

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
            h_ini = datetime.now().strftime('%Y-%m-%d')
            self.card_total.val_label.setText(str(BarangModel.get_total_count()))
            self.card_kritis.val_label.setText(str(BarangModel.get_kritis_count()))
            self.card_masuk.val_label.setText(str(TransaksiModel.get_daily_count('MASUK', h_ini)))
            self.card_keluar.val_label.setText(str(TransaksiModel.get_daily_count('KELUAR', h_ini)))
            
            dates, data_in, data_out = [], [], []
            timeframe_val = self.combo_timeframe.currentText()
            
            if timeframe_val == "1 Tahun Terakhir":
                for i in range(11, -1, -1):
                    current_date = datetime.now()
                    target_month = current_date.month - i
                    target_year = current_date.year
                    while target_month <= 0:
                        target_month += 12
                        target_year -= 1
                    period_str = f"{target_year}-{target_month:02d}"
                    label_str = datetime(target_year, target_month, 1).strftime('%b %y')
                    dates.append(label_str)
                    data_in.append(TransaksiModel.get_daily_count('MASUK', period_str))
                    data_out.append(TransaksiModel.get_daily_count('KELUAR', period_str))
            else:
                days_count = 30 if timeframe_val == "30 Hari Terakhir" else 7
                for i in range(days_count - 1, -1, -1):
                    t = (datetime.now() - timedelta(days=i))
                    dates.append(t.strftime('%d %b'))
                    t_str = t.strftime('%Y-%m-%d')
                    data_in.append(TransaksiModel.get_daily_count('MASUK', t_str))
                    data_out.append(TransaksiModel.get_daily_count('KELUAR', t_str))
                    
            self.update_charts(dates, data_in, data_out)
            self.refresh_monitor_table()
            self.refresh_prediksi_table()
            self.refresh_analytics()
        except Exception as e: print(f"Dashboard Refresh Error: {e}")

    def refresh_analytics(self):
        try:
            # --- PIE KATEGORI ---
            cat_data = BarangModel.get_distribusi_kategori()
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
            rak_data = BarangModel.get_distribusi_rak()
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
        except Exception as e: print(f"Analytics Error: {e}")

    def refresh_monitor_table(self):
        try:
            f_val = self.combo_filter_kritis.currentText()
            rows = BarangModel.get_kritis_data(category=f_val, limit=20)
            self.table_kritis.setRowCount(0)
            
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
            self.adjust_table_height()
        except Exception as e: print(f"Table Error: {e}")

    def refresh_prediksi_table(self):
        try:
            rows = TransaksiModel.get_recent_out_transactions(days=30)
            
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
                    
            self.adjust_table_height()
        except Exception as e: print(f"Prediksi ML Error: {e}")