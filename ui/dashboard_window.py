import os
import sys
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QSpacerItem, 
    QSizePolicy, QSystemTrayIcon, QMenu, QScrollArea
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon, QFont, QAction

# Import halaman UI
from ui.master_barang_page import MasterBarangPage
from ui.master_pendukung_page import MasterPendukungPage
from ui.barang_masuk_page import BarangMasukPage
from ui.barang_keluar_page import BarangKeluarPage
from ui.dashboard_page import DashboardPage
from ui.laporan_page import LaporanPage
from ui.pengaturan_page import PengaturanPage
from ui.log_aktivitas_page import LogAktivitasPage
from ui.barang_form_page import BarangFormPage
from ui.audit_stok_page import AuditStokPage
from database.connection import get_connection
from PySide6.QtWidgets import QMessageBox

class DashboardWindow(QMainWindow):
    """
    Jendela Utama Aplikasi (Main Shell).
    Didesain responsif untuk berbagai resolusi layar laptop.
    """

    def __init__(self):
        super().__init__()
        self.already_warned = False
        self._force_close = False
        self.init_settings()
        self.init_ui()
        self.setup_tray()

    def showEvent(self, event):
        super().showEvent(event)
        self.check_stok_kritis()

    def check_stok_kritis(self):
        if self.already_warned: return
        self.already_warned = True
        
        try:
            conn = get_connection()
            if conn is None: return
            cursor = conn.cursor()
            cursor.execute("SELECT nama_barang, stok, stok_minimum FROM barang_baru WHERE stok <= stok_minimum")
            kritis = cursor.fetchall()
            conn.close()
            
            if kritis:
                teks_kritis = "\n".join([f"- {r[0]} (Sisa: {r[1]}, Min: {r[2]})" for r in kritis])
                msg = QMessageBox(self)
                msg.setWindowTitle("⚠️ PERINGATAN DARURAT STOK GUDANG")
                msg.setText(f"Halo Admin, terdapat {len(kritis)} barang yang akan atau sudah habis! Harap segera hubungi Suplier untuk pengadaan (restock):\n\n{teks_kritis}")
                msg.setIcon(QMessageBox.Warning)
                msg.setStyleSheet("QMessageBox { background-color: white; } QLabel { color: #b91c1c; font-size: 13px; font-weight: bold; } QPushButton { background-color: #ef4444; color: white; padding: 5px 20px; font-weight: bold; border-radius: 6px; }")
                msg.exec()
        except Exception as e:
            print(f"Check Stok Kritis Error: {e}")

    def init_settings(self):
        """Konfigurasi jendela utama agar adaptif."""
        self.setWindowTitle("PTPN IV - Inventory Management System")
        
        # Set ukuran minimum agar UI tidak rusak di layar sangat kecil
        self.setMinimumSize(1100, 700)
        
        # Load Window Icon
        icon_path = self.get_asset_path("Logo PTPN IV.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet(self.get_main_style())
        
        # OTOMATIS MAKSIMALKAN LAYAR SAAT DIBUKA
        self.showMaximized()
        self.activateWindow()

    def get_asset_path(self, filename):
        """Helper path asset yang aman untuk EXE."""
        from utils.path_helper import get_resource_path
        return get_resource_path(os.path.join("assets", "images", filename))

    def init_ui(self):
        """Membangun struktur layout Utama yang fleksibel."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. SIDEBAR NAVIGATION
        self.setup_sidebar()

        # 2. CONTENT AREA
        self.setup_content_area()

        # Default Page
        self.switch_page(0)

    def setup_sidebar(self):
        """Konfigurasi Sidebar Navigasi dengan identitas unit."""
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(260)
        
        self.sidebar_scroll = QScrollArea(self.sidebar)
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar { width: 0px; }")
        
        self.sidebar_content = QWidget()
        self.sidebar_content.setObjectName("sidebarContent")
        self.sidebar_content.setStyleSheet("background: transparent;")
        
        sidebar_layout = QVBoxLayout(self.sidebar_content)
        sidebar_layout.setContentsMargins(0, 30, 0, 20)
        sidebar_layout.setSpacing(5)

        self.sidebar_scroll.setWidget(self.sidebar_content)

        sidebar_wrapper = QVBoxLayout(self.sidebar)
        sidebar_wrapper.setContentsMargins(0, 0, 0, 0)
        sidebar_wrapper.addWidget(self.sidebar_scroll)

        # --- LOGO & UNIT NAME SECTION ---
        brand_container = QWidget()
        brand_layout = QVBoxLayout(brand_container)
        brand_layout.setSpacing(12)
        brand_layout.setContentsMargins(15, 0, 15, 0)

        self.brand_logo = QLabel()
        pixmap = QPixmap(self.get_asset_path("Logo PTPN IV.png"))
        if not pixmap.isNull():
            self.brand_logo.setPixmap(pixmap.scaled(140, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.brand_logo.setText("LOGO")
            self.brand_logo.setStyleSheet("color: white; font-weight: bold;")
        self.brand_logo.setAlignment(Qt.AlignCenter)

        # Label Identitas Unit Kerja
        self.unit_name = QLabel("PTPN IV\nKEBUN ADOLINA")
        self.unit_name.setAlignment(Qt.AlignCenter)
        self.unit_name.setStyleSheet("""
            color: #f8fafc; 
            font-size: 13px; 
            font-weight: 800; 
            letter-spacing: 1.5px;
            line-height: 1.3;
        """)

        brand_layout.addWidget(self.brand_logo)
        brand_layout.addWidget(self.unit_name)
        sidebar_layout.addWidget(brand_container)
        
        sidebar_layout.addSpacing(30)

        # Menu Buttons
        self.btn_dashboard = self.create_nav_btn("  🏠  Dashboard", 0)
        self.btn_master_parent = self.create_nav_btn("  📂  Master Data", -1, is_parent=True)
        
        # Sub Menu Container
        self.sub_menu_frame = QFrame()
        self.sub_menu_frame.setObjectName("subMenuFrame")
        self.sub_menu_frame.setVisible(False)
        self.sub_menu_frame.setFixedHeight(135) 
        sub_layout = QVBoxLayout(self.sub_menu_frame)
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.setSpacing(0)
        
        self.btn_barang = self.create_nav_btn("📦  Master Barang", 1, is_sub=True)
        self.btn_pendukung = self.create_nav_btn("⚙️  Master Pendukung", 2, is_sub=True)
        self.btn_barang_form = self.create_nav_btn("📝  Barang Form", 8, is_sub=True)
        
        sub_layout.addWidget(self.btn_barang)
        sub_layout.addWidget(self.btn_pendukung)
        sub_layout.addWidget(self.btn_barang_form)
        
        self.btn_masuk = self.create_nav_btn("  📥  Barang Masuk", 3)
        self.btn_keluar = self.create_nav_btn("  📤  Barang Keluar", 4)
        self.btn_audit = self.create_nav_btn("  ⚖️  Audit Stok", 9)
        self.btn_laporan = self.create_nav_btn("  📊  Laporan Sistem", 5)
        self.btn_log = self.create_nav_btn("  🕵️  Log Aktivitas", 7)
        self.btn_pengaturan = self.create_nav_btn("  🛡️  Pengaturan Sistem", 6)

        # Tambahkan ke Sidebar
        sidebar_layout.addWidget(self.btn_dashboard)
        sidebar_layout.addWidget(self.btn_master_parent)
        sidebar_layout.addWidget(self.sub_menu_frame)
        sidebar_layout.addWidget(self.btn_masuk)
        sidebar_layout.addWidget(self.btn_keluar)
        sidebar_layout.addWidget(self.btn_audit)
        sidebar_layout.addWidget(self.btn_laporan)
        sidebar_layout.addWidget(self.btn_log)
        sidebar_layout.addWidget(self.btn_pengaturan)
        
        sidebar_layout.addStretch()

        # Logout Section
        self.btn_logout = QPushButton("  🚪  Keluar Akun")
        self.btn_logout.setObjectName("btnLogout")
        self.btn_logout.setCursor(Qt.PointingHandCursor)
        self.btn_logout.setFixedHeight(50)
        self.btn_logout.clicked.connect(self.logout)
        sidebar_layout.addWidget(self.btn_logout)

        self.main_layout.addWidget(self.sidebar)

        # Mapping Navigasi
        self.nav_buttons = {
            0: self.btn_dashboard,
            1: self.btn_barang,
            2: self.btn_pendukung,
            8: self.btn_barang_form,
            3: self.btn_masuk,
            4: self.btn_keluar,
            9: self.btn_audit,
            5: self.btn_laporan,
            7: self.btn_log,
            6: self.btn_pengaturan
        }

    def create_nav_btn(self, text, index, is_parent=False, is_sub=False):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(50 if not is_sub else 45)
        
        if is_sub:
            btn.setObjectName("subNavLink")
        elif is_parent:
            btn.setObjectName("parentNavLink")
            btn.clicked.connect(self.toggle_master_menu)
        else:
            btn.setObjectName("navLink")

        if index != -1:
            btn.clicked.connect(lambda checked=False, idx=index: self.nav_button_clicked(idx))
        return btn

    def setup_content_area(self):
        """Area konten dengan stacked widget untuk efisiensi layar."""
        # Container area kanan dengan background konsisten
        content_area = QWidget()
        content_area.setObjectName("contentArea")
        content_area.setStyleSheet("""
            QWidget#contentArea { background-color: #f8fafc; }
            QStackedWidget { background-color: #f8fafc; }
        """)
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.pages = QStackedWidget()
        content_layout.addWidget(self.pages)
        
        # Bungkus setiap halaman agar memiliki header dan padding yang konsisten
        self.pages.addWidget(self.create_page_wrapper(DashboardPage(), "Dashboard Overview", "Statistik aktivitas inventaris real-time."))
        
        # Pages with Signals
        self.master_barang_page = MasterBarangPage()
        self.barang_form_page = BarangFormPage()
        self.audit_stok_page = AuditStokPage()
        
        # Connections
        self.master_barang_page.add_requested.connect(self.go_to_add_barang)
        self.master_barang_page.edit_requested.connect(self.go_to_edit_barang)
        self.barang_form_page.back_requested.connect(lambda: self.switch_page(1))
        self.barang_form_page.barang_saved.connect(self.master_barang_page.load_barang)

        self.pages.addWidget(self.create_page_wrapper(self.master_barang_page, "Database Barang", "Kelola seluruh item dan stok inventaris."))
        self.pages.addWidget(self.create_page_wrapper(MasterPendukungPage(), "Konfigurasi Pendukung", "Pengaturan Kategori dan Lokasi Penyimpanan."))
        self.pages.addWidget(self.create_page_wrapper(BarangMasukPage(), "Transaksi Masuk", "Catat pengadaan barang baru ke dalam sistem."))
        self.pages.addWidget(self.create_page_wrapper(BarangKeluarPage(), "Transaksi Keluar", "Catat distribusi dan pengeluaran barang."))
        self.pages.addWidget(self.create_page_wrapper(LaporanPage(), "Laporan Aktivitas", "Analisa data pergerakan barang berdasarkan periode."))
        self.pages.addWidget(self.create_page_wrapper(PengaturanPage(), "Keamanan & Pengaturan", "Sistem Kelola Database Backup dan Restore Sistem."))
        self.pages.addWidget(self.create_page_wrapper(LogAktivitasPage(), "Log Aktivitas Rekam Jejak", "Pemantauan aktivitas pengguna sistem secara komprehensif."))
        
        # New Pages Slots
        self.pages.addWidget(self.create_page_wrapper(self.barang_form_page, "Formulir Barang", "Kelola informasi detail spesifik barang.")) # Index 8
        self.pages.addWidget(self.create_page_wrapper(self.audit_stok_page, "Audit Stok Opname", "Verifikasi fisik barang secara periodik.")) # Index 9

        self.main_layout.addWidget(content_area)

    def create_page_wrapper(self, content_widget, title, subtitle):
        """Standardisasi tampilan header setiap halaman."""
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(0)

        # Header Section
        header = QWidget()
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 20)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 26px; font-weight: 800; color: #000000;")
        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet("font-size: 14px; color: #000000; font-weight: 400;")
        
        h_layout.addWidget(lbl_title)
        h_layout.addWidget(lbl_sub)
        
        layout.addWidget(header)
        layout.addWidget(content_widget, 1) # Berikan stretch factor 1 agar mengisi ruang
        return wrapper

    def go_to_add_barang(self):
        self.barang_form_page.set_add_mode()
        self.switch_page(8)

    def go_to_edit_barang(self, id_b, data):
        self.barang_form_page.set_edit_mode(id_b, data)
        self.switch_page(8)

    def get_main_style(self):
        return """
            QMainWindow { background-color: #f8fafc; }
            #sidebar { 
                background-color: #1e293b; 
                border-right: 1px solid #e2e8f0;
            }
            QPushButton#navLink, QPushButton#parentNavLink {
                color: #94a3b8;
                background-color: transparent;
                border: none;
                border-left: 4px solid transparent;
                text-align: left;
                padding-left: 20px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton#navLink:hover, QPushButton#parentNavLink:hover {
                color: #f8fafc;
                background-color: #334155;
            }
            QPushButton#navLink[active="true"] {
                color: #ffffff;
                background-color: #334155;
                border-left: 4px solid #3b82f6;
            }
            QPushButton#subNavLink {
                color: #94a3b8;
                background-color: #1a2232;
                border: none;
                text-align: left;
                padding-left: 55px;
                font-size: 13px;
            }
            QPushButton#subNavLink:hover {
                color: white;
                background-color: #334155;
            }
            QPushButton#subNavLink[active="true"] {
                color: #3b82f6;
                font-weight: bold;
            }
            #btnLogout {
                color: #fca5a5;
                background: transparent;
                border: none;
                border-top: 1px solid #334155;
                padding: 15px;
                font-weight: bold;
                text-align: left;
                padding-left: 25px;
            }
            #btnLogout:hover {
                background-color: #ef4444;
                color: white;
            }
            #pageContentBody { background-color: transparent; }
        """

    def toggle_master_menu(self):
        is_visible = self.sub_menu_frame.isVisible()
        self.sub_menu_frame.setVisible(not is_visible)

    def nav_button_clicked(self, index):
        """Dipanggil HANYA saat tombol navigasi kiri diklik, untuk memastikan form bersih."""
        if index == 8: # Barang Form
            self.barang_form_page.clear_form()
            self.barang_form_page.set_add_mode()
        elif index == 3: # Barang Masuk
            widget = self.pages.widget(3).findChild(QWidget, "contentArea") or self.pages.widget(3).layout().itemAt(1).widget()
            if hasattr(widget, 'clear_form'): widget.clear_form()
        elif index == 4: # Barang Keluar
            widget = self.pages.widget(4).findChild(QWidget, "contentArea") or self.pages.widget(4).layout().itemAt(1).widget()
            if hasattr(widget, 'clear_form'): widget.clear_form()
        
        self.switch_page(index)

    def switch_page(self, index):
        self.pages.setCurrentIndex(index)
        for idx, btn in self.nav_buttons.items():
            is_active = (idx == index)
            btn.setProperty("active", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def logout(self):
        self._force_close = True
        from ui.login_window import LoginWindow
        self.login_win = LoginWindow()
        self.login_win.show()
        self.close()

    def setup_tray(self):
        """Konfigurasi Ikon di System Tray Windows."""
        icon_path = self.get_asset_path("Logo PTPN IV.png")
        if not os.path.exists(icon_path):
            return

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(icon_path))
        self.tray_icon.setToolTip("PTPN IV Inventory System")

        # Context Menu Tray
        tray_menu = QMenu()
        
        show_action = QAction("📂 Tampilkan Aplikasi", self)
        show_action.triggered.connect(self.show_and_restore)
        
        exit_action = QAction("❌ Keluar Sepenuhnya", self)
        exit_action.triggered.connect(self.force_quit)

        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger: # Klik kiri sekali
            self.show_and_restore()

    def show_and_restore(self):
        """Kembalikan jendela ke state terakhir (Maximized/Normal)."""
        if self.isHidden():
            self.show()
        
        if self.isMinimized():
            self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        
        self.raise_()
        self.activateWindow()

    def force_quit(self):
        self._force_close = True
        self.close()

    def closeEvent(self, event):
        """Tangkap event tutup untuk sembunyi ke tray alih-alih keluar."""
        if self._force_close:
            event.accept()
        else:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Info Sistem",
                "Aplikasi tetap berjalan di System Tray untuk memantau stok.",
                QSystemTrayIcon.Information,
                3000
            )

    def send_tray_notification(self, title, message, icon=QSystemTrayIcon.Warning):
        """Helper untuk mengirim notifikasi balon Windows."""
        if hasattr(self, 'tray_icon'):
            self.tray_icon.showMessage(title, message, icon, 5000)