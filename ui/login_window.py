import os
import sys
from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QPixmap, QIcon, QFont

from models.user_model import login_user
from ui.dashboard_window import DashboardWindow
from utils.barcode_utils import sync_barcodes

class LoginWindow(QWidget):
    """
    Jendela Login Utama untuk Aplikasi Management Barang PTPN IV.
    Didesain dengan gaya modern, clean, dan profesional.
    """

    def __init__(self):
        super().__init__()
        self.init_settings()
        self.init_ui()

    def init_settings(self):
        """Konfigurasi dasar jendela."""
        self.setWindowTitle("PTPN IV - Inventory System")
        self.setMinimumSize(900, 600)
        self.showMaximized()
        self.setWindowIcon(QIcon(self.get_asset_path("Logo PTPN IV.png")))
        self.setStyleSheet(self.get_main_style())

    def get_asset_path(self, filename):
        """Helper path asset."""
        from utils.path_helper import get_resource_path
        return get_resource_path(os.path.join("assets", "images", filename))

    def init_ui(self):
        """Inisialisasi layout dan widget."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Center wrapping layout
        center_layout = QHBoxLayout()
        center_layout.addStretch()

        # --- CONTAINER UTAMA (Floating Card) ---
        container = QFrame()
        container.setObjectName("mainContainer")
        container.setFixedSize(450, 600)
        
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 30))
        container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(45, 50, 45, 50)
        container_layout.setSpacing(10)

        # 1. Bagian Logo
        self.logo_label = QLabel()
        pixmap = QPixmap(self.get_asset_path("Logo PTPN IV.png"))
        if not pixmap.isNull():
            self.logo_label.setPixmap(pixmap.scaled(140, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.logo_label.setText("PTPN IV")
            self.logo_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #1e293b;")
        
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setContentsMargins(0, 0, 0, 15)

        # 2. Judul & Deskripsi
        title = QLabel("Inventory System")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Manajemen Barang Kebun Adolina")
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignCenter)

        # 3. Input Form
        form_frame = QFrame()
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(0, 25, 0, 15)
        form_layout.setSpacing(18)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.username.setFixedHeight(50)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setFixedHeight(50)

        self.toggle_action = QAction("👁️‍🗨️", self)
        self.password.addAction(self.toggle_action, QLineEdit.TrailingPosition)
        self.toggle_action.triggered.connect(self.toggle_password_visibility)

        form_layout.addWidget(self.username)
        form_layout.addWidget(self.password)

        # 4. Tombol Aksi
        self.btn_login = QPushButton("MASUK KE SISTEM")
        self.btn_login.setFixedHeight(55)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.clicked.connect(self.proses_login)

        self.btn_register = QPushButton("Belum punya akun? Daftar")
        self.btn_register.setObjectName("btnLink")
        self.btn_register.setCursor(Qt.PointingHandCursor)
        self.btn_register.clicked.connect(self.open_register)

        # Susun Semuanya
        container_layout.addWidget(self.logo_label)
        container_layout.addWidget(title)
        container_layout.addWidget(subtitle)
        container_layout.addWidget(form_frame)
        container_layout.addSpacing(15)
        container_layout.addWidget(self.btn_login)
        container_layout.addWidget(self.btn_register, alignment=Qt.AlignCenter)
        container_layout.addStretch()

        center_layout.addWidget(container)
        center_layout.addStretch()
        
        main_layout.addStretch()
        main_layout.addLayout(center_layout)
        main_layout.addStretch()

        # Event: Enter key on password field
        self.password.returnPressed.connect(self.proses_login)

    def get_main_style(self):
        """Kumpulan CSS Modern untuk jendela login."""
        return """
            QWidget {
                background-color: #f1f5f9;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            #mainContainer {
                background-color: #ffffff;
                border-radius: 16px;
            }
            #titleLabel {
                font-size: 26px;
                font-weight: 800;
                color: #1e293b;
            }
            #subtitleLabel {
                font-size: 13px;
                color: #64748b;
                font-weight: 400;
            }
            QLineEdit {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 10px 15px;
                background-color: #f8fafc;
                color: #1e293b;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #3b82f6;
                background-color: #ffffff;
            }
            QPushButton {
                background-color: #1e293b;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
            QPushButton:pressed {
                background-color: #0f172a;
            }
            #btnLink {
                background: none;
                border: none;
                color: #3b82f6;
                font-size: 13px;
                font-weight: 600;
                text-decoration: underline;
            }
            #btnLink:hover {
                color: #2563eb;
            }
        """

    def toggle_password_visibility(self):
        """Menukar mode tampilan password (Tersembunyi/Terlihat)."""
        if self.password.echoMode() == QLineEdit.Password:
            self.password.setEchoMode(QLineEdit.Normal)
            self.toggle_action.setText("👁️")
        else:
            self.password.setEchoMode(QLineEdit.Password)
            self.toggle_action.setText("🔒")

    def proses_login(self):
        """Menangani verifikasi kredensial pengguna."""
        user_val = self.username.text().strip()
        pass_val = self.password.text().strip()

        if not user_val or not pass_val:
            self.show_notif("Peringatan", "Mohon isi username dan password Anda.", is_error=True)
            return

        # Animasi feedback visual (Sederhana: Ubah teks tombol)
        self.btn_login.setText("MEMVERIFIKASI...")
        self.btn_login.setEnabled(False)

        user = login_user(user_val, pass_val)

        if user:
            sync_barcodes()
            self.dashboard = DashboardWindow(user_data=user)
            self.dashboard.show()
            self.close()
        else:
            self.btn_login.setText("MASUK KE SISTEM")
            self.btn_login.setEnabled(True)
            self.show_notif("Login Gagal", "Username atau Password yang Anda masukkan salah.", is_error=True)

    def show_notif(self, title, message, is_error=False):
        """Menampilkan kotak pesan yang sudah di-style."""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(QMessageBox.Critical if is_error else QMessageBox.Information)
        msg.setStyleSheet("QLabel{ color: black; font-size: 13px; } QPushButton{ width: 80px; }")
        msg.exec()

    def open_register(self):
        """Membuka jendela registrasi."""
        from ui.register_window import RegisterWindow
        self.register = RegisterWindow()
        self.register.show()
        self.close()