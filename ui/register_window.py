import os
import sys
from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon

from models.user_model import register_user

class RegisterWindow(QWidget):
    """
    Jendela Registrasi Pengguna.
    Didesain seragam dengan LoginWindow untuk konsistensi UI/UX.
    """

    def __init__(self):
        super().__init__()
        self.init_settings()
        self.init_ui()

    def init_settings(self):
        """Konfigurasi dasar jendela registrasi."""
        self.setWindowTitle("PTPN IV - Create Account")
        self.setMinimumSize(900, 600)
        self.showMaximized()
        self.setWindowIcon(QIcon(self.get_asset_path("Logo PTPN IV.png")))
        self.setStyleSheet(self.get_main_style())

    def get_asset_path(self, filename):
        """Helper untuk mengambil path file asset."""
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, "assets", "images", filename)

    def init_ui(self):
        """Inisialisasi antarmuka pengguna."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Center wrapping layout
        center_layout = QHBoxLayout()
        center_layout.addStretch()

        # Container Utama (Floating Card)
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

        # 1. Logo Section
        self.logo_label = QLabel()
        pixmap = QPixmap(self.get_asset_path("Logo PTPN IV.png"))
        if not pixmap.isNull():
            self.logo_label.setPixmap(pixmap.scaled(140, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.logo_label.setText("PTPN IV")
            self.logo_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #1e293b;")
        
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setContentsMargins(0, 0, 0, 15)

        # 2. Header Section
        title = QLabel("Create Account")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Daftarkan akun baru untuk akses sistem")
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignCenter)

        # 3. Form Section
        form_frame = QFrame()
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(0, 25, 0, 15)
        form_layout.setSpacing(18)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Pilih Username")
        self.username.setFixedHeight(50)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Pilih Password")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setFixedHeight(50)

        form_layout.addWidget(self.username)
        form_layout.addWidget(self.password)

        # 4. Action Section
        self.btn_register = QPushButton("DAFTAR SEKARANG")
        self.btn_register.setFixedHeight(55)
        self.btn_register.setCursor(Qt.PointingHandCursor)
        self.btn_register.clicked.connect(self.proses_register)

        self.btn_back = QPushButton("Sudah punya akun? Login")
        self.btn_back.setObjectName("btnLink")
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(self.back_login)

        # Susun widget
        container_layout.addWidget(self.logo_label)
        container_layout.addWidget(title)
        container_layout.addWidget(subtitle)
        container_layout.addWidget(form_frame)
        container_layout.addSpacing(15)
        container_layout.addWidget(self.btn_register)
        container_layout.addWidget(self.btn_back, alignment=Qt.AlignCenter)
        container_layout.addStretch()

        center_layout.addWidget(container)
        center_layout.addStretch()
        
        main_layout.addStretch()
        main_layout.addLayout(center_layout)
        main_layout.addStretch()

    def get_main_style(self):
        """Kumpulan CSS Modern (Sinkron dengan LoginWindow)."""
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
                border: 2px solid #10b981; /* Warna hijau untuk registrasi */
                background-color: #ffffff;
            }
            QPushButton {
                background-color: #10b981; /* Hijau PTPN IV Style */
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
            #btnLink {
                background: none;
                border: none;
                color: #64748b;
                font-size: 13px;
                font-weight: 600;
                text-decoration: underline;
            }
            #btnLink:hover {
                color: #1e293b;
            }
        """

    def proses_register(self):
        """Logika proses pendaftaran akun."""
        username = self.username.text().strip()
        password = self.password.text().strip()

        if not username or not password:
            self.show_notif("Peringatan", "Mohon lengkapi username dan password.", is_error=True)
            return

        self.btn_register.setText("MEMPROSES...")
        self.btn_register.setEnabled(False)

        success = register_user(username, password)

        if success:
            self.show_notif("Sukses", f"Akun '{username}' berhasil dibuat! Silahkan login.")
            self.back_login()
        else:
            self.btn_register.setText("DAFTAR SEKARANG")
            self.btn_register.setEnabled(True)
            self.show_notif("Gagal", "Username sudah digunakan oleh pengguna lain.", is_error=True)

    def show_notif(self, title, message, is_error=False):
        """Pesan notifikasi dengan teks hitam yang jelas."""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(QMessageBox.Critical if is_error else QMessageBox.Information)
        msg.setStyleSheet("QLabel{ color: black; font-size: 13px; } QPushButton{ width: 80px; color: black; font-weight: bold; background-color: #f1f5f9; border: 1px solid #cbd5e1; }")
        msg.exec()

    def back_login(self):
        """Kembali ke jendela Login."""
        from ui.login_window import LoginWindow
        self.login = LoginWindow()
        self.login.show()
        self.close()