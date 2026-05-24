"""
Dialog Profil Pengguna — Untuk mengelola foto profil, nama, dan info akun.
Mendukung upload foto profil dengan preview, crop otomatis menjadi lingkaran,
dan penyimpanan ke folder assets/profile_photos.
"""

import os
import shutil
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QFileDialog, QGraphicsDropShadowEffect, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QPainter, QBrush, QPainterPath, QColor, QFont
from database.connection import get_connection
from models.user_model import update_user_nama
from utils.path_helper import get_root_dir


def get_profile_photo_dir():
    """Mendapatkan path folder penyimpanan foto profil."""
    base = get_root_dir()
    photo_dir = os.path.join(base, "assets", "profile_photos")
    os.makedirs(photo_dir, exist_ok=True)
    return photo_dir


def get_user_photo_path(user_id):
    """Mendapatkan path foto profil user berdasarkan ID."""
    conn = None
    try:
        conn = get_connection()
        if conn is None:
            return ""
        cursor = conn.cursor()
        cursor.execute("SELECT profile_photo FROM users WHERE id_user = ?", (user_id,))
        row = cursor.fetchone()
        if row and row['profile_photo']:
            photo_path = os.path.join(get_profile_photo_dir(), row['profile_photo'])
            if os.path.exists(photo_path):
                return photo_path
    except Exception as e:
        print(f"get_user_photo_path Error: {e}")
    finally:
        if conn:
            conn.close()
    return ""


def save_user_photo(user_id, filename):
    """Simpan nama file foto profil ke database."""
    conn = None
    try:
        conn = get_connection()
        if conn is None:
            return False
        conn.execute("UPDATE users SET profile_photo = ? WHERE id_user = ?", (filename, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"save_user_photo Error: {e}")
        return False
    finally:
        if conn:
            conn.close()


def create_circular_pixmap(pixmap, size=120):
    """Buat pixmap bulat dari gambar persegi/persegi panjang."""
    if pixmap.isNull():
        return pixmap

    # Scale ke ukuran yang diinginkan (crop center)
    scaled = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

    # Crop tengah jika tidak persegi
    x = (scaled.width() - size) // 2
    y = (scaled.height() - size) // 2
    cropped = scaled.copy(x, y, size, size)

    # Buat mask bulat
    result = QPixmap(size, size)
    result.fill(Qt.transparent)

    painter = QPainter(result)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, cropped)
    painter.end()

    return result


def get_default_avatar_pixmap(username="U", size=120):
    """Buat avatar default (lingkaran dengan inisial)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Lingkaran background gradient
    painter.setBrush(QBrush(QColor("#6366f1")))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(0, 0, size, size)

    # Inisial huruf
    painter.setPen(QColor("#ffffff"))
    font = QFont("Segoe UI", int(size * 0.38), QFont.Bold)
    painter.setFont(font)
    initials = username[0].upper() if username else "U"
    painter.drawText(0, 0, size, size, Qt.AlignCenter, initials)

    painter.end()
    return pixmap


class ToastNotification(QLabel):
    """Notifikasi toast ringan yang muncul di atas dialog lalu menghilang."""

    def __init__(self, message, parent=None, success=True):
        super().__init__(message, parent)
        bg = "#059669" if success else "#dc2626"
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: white;
                padding: 10px 24px;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 700;
            }}
        """)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(44)
        self.adjustSize()
        self.setMinimumWidth(260)

    def show_toast(self, duration=2500):
        """Tampilkan toast lalu hilangkan otomatis."""
        if self.parent():
            pw = self.parent().width()
            self.move((pw - self.width()) // 2, 12)
        self.show()
        self.raise_()
        QTimer.singleShot(duration, self._fade_out)

    def _fade_out(self):
        self.hide()
        self.deleteLater()


class ProfileDialog(QDialog):
    """Dialog untuk mengelola profil pengguna (foto, nama)."""
    photo_updated = Signal()
    nama_updated = Signal(str)

    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.user_id = user_data.get('id_user', 0)
        self.username = user_data.get('username', 'User')
        self.display_name = user_data.get('nama', '') or self.username
        self.role = user_data.get('role', 'user')
        self.setWindowTitle("Profil Pengguna")
        self.setFixedSize(420, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #f8fafc;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        # ===== CARD PROFIL =====
        card = QFrame()
        card.setObjectName("profileCard")
        card.setStyleSheet("""
            QFrame#profileCard {
                background-color: #ffffff;
                border-radius: 20px;
                border: 1px solid #e2e8f0;
            }
        """)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 30))
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 25, 30, 20)
        card_layout.setSpacing(12)
        card_layout.setAlignment(Qt.AlignCenter)

        # --- Foto Profil ---
        self.photo_label = QLabel()
        self.photo_label.setFixedSize(130, 130)
        self.photo_label.setAlignment(Qt.AlignCenter)
        self.photo_label.setCursor(Qt.PointingHandCursor)
        self.photo_label.setToolTip("Klik untuk ganti foto")
        self.photo_label.mousePressEvent = lambda e: self.change_photo()
        self._load_photo()

        photo_container = QHBoxLayout()
        photo_container.addStretch()
        photo_container.addWidget(self.photo_label)
        photo_container.addStretch()
        card_layout.addLayout(photo_container)

        # --- Role Badge ---
        if self.role == 'super_admin':
            badge_text = "🛡️ SUPER ADMIN"
            badge_bg = "#059669"
        else:
            badge_text = "👁️ MONITORING"
            badge_bg = "#6366f1"

        role_badge = QLabel(badge_text)
        role_badge.setAlignment(Qt.AlignCenter)
        role_badge.setFixedHeight(28)
        role_badge.setStyleSheet(f"""
            color: #ffffff;
            background-color: {badge_bg};
            border-radius: 12px;
            padding: 4px 20px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.5px;
        """)
        badge_container = QHBoxLayout()
        badge_container.addStretch()
        badge_container.addWidget(role_badge)
        badge_container.addStretch()
        card_layout.addLayout(badge_container)

        # --- Username (read-only) ---
        uname_lbl = QLabel(f"@{self.username}")
        uname_lbl.setAlignment(Qt.AlignCenter)
        uname_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 500;")
        card_layout.addWidget(uname_lbl)

        layout.addWidget(card)

        # ===== FORM NAMA =====
        nama_frame = QFrame()
        nama_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 14px;
                border: 1px solid #e2e8f0;
            }
        """)
        nama_layout = QVBoxLayout(nama_frame)
        nama_layout.setContentsMargins(20, 16, 20, 16)
        nama_layout.setSpacing(8)

        nama_title = QLabel("✏️  Nama Tampilan")
        nama_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #475569; border: none;")
        nama_layout.addWidget(nama_title)

        self.nama_input = QLineEdit()
        self.nama_input.setText(self.display_name)
        self.nama_input.setPlaceholderText("Masukkan nama lengkap Anda")
        self.nama_input.setFixedHeight(42)
        self.nama_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                padding: 8px 14px;
                font-size: 14px;
                color: #1e293b;
                background-color: #f8fafc;
            }
            QLineEdit:focus {
                border-color: #818cf8;
                background-color: #ffffff;
            }
        """)
        nama_layout.addWidget(self.nama_input)

        btn_save_nama = QPushButton("💾  Simpan Nama")
        btn_save_nama.setCursor(Qt.PointingHandCursor)
        btn_save_nama.setFixedHeight(40)
        btn_save_nama.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        btn_save_nama.clicked.connect(self.save_nama)
        nama_layout.addWidget(btn_save_nama)

        layout.addWidget(nama_frame)

        # ===== TOMBOL FOTO =====
        btn_change = QPushButton("📷  Ganti Foto Profil")
        btn_change.setCursor(Qt.PointingHandCursor)
        btn_change.setFixedHeight(44)
        btn_change.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #8b5cf6);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #7c3aed);
            }
        """)
        btn_change.clicked.connect(self.change_photo)
        layout.addWidget(btn_change)

        btn_remove = QPushButton("🗑️  Hapus Foto")
        btn_remove.setCursor(Qt.PointingHandCursor)
        btn_remove.setFixedHeight(38)
        btn_remove.setStyleSheet("""
            QPushButton {
                background-color: #fef2f2;
                color: #dc2626;
                border: 1px solid #fecaca;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #fee2e2;
                border-color: #f87171;
            }
        """)
        btn_remove.clicked.connect(self.remove_photo)
        layout.addWidget(btn_remove)

        layout.addStretch()

    def _show_toast(self, msg, success=True):
        """Tampilkan toast notification di atas dialog."""
        toast = ToastNotification(msg, self, success=success)
        toast.show_toast()

    def _load_photo(self):
        """Muat foto profil dari database/file."""
        photo_path = get_user_photo_path(self.user_id)
        if photo_path and os.path.exists(photo_path):
            pixmap = QPixmap(photo_path)
            circular = create_circular_pixmap(pixmap, 120)
        else:
            circular = get_default_avatar_pixmap(self.display_name, 120)
        self.photo_label.setPixmap(circular)

    def save_nama(self):
        """Simpan perubahan nama tampilan."""
        new_nama = self.nama_input.text().strip()
        if not new_nama:
            self._show_toast("⚠️ Nama tidak boleh kosong!", success=False)
            return

        if update_user_nama(self.user_id, new_nama):
            self.display_name = new_nama
            self.user_data['nama'] = new_nama
            self.nama_updated.emit(new_nama)
            self._show_toast("✅ Nama berhasil diperbarui!")
        else:
            self._show_toast("❌ Gagal menyimpan nama.", success=False)

    def change_photo(self):
        """Buka file dialog untuk memilih foto baru."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih Foto Profil",
            "",
            "Gambar (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not file_path:
            return

        # Validasi ukuran (max 5MB)
        file_size = os.path.getsize(file_path)
        if file_size > 5 * 1024 * 1024:
            self._show_toast("⚠️ Ukuran foto maksimal 5MB!", success=False)
            return

        try:
            # Hapus foto lama dari disk terlebih dahulu agar tidak menumpuk
            old_photo_path = get_user_photo_path(self.user_id)
            if old_photo_path and os.path.exists(old_photo_path):
                try:
                    os.remove(old_photo_path)
                except Exception as ex:
                    print(f"Gagal menghapus foto lama: {ex}")

            # Salin file ke folder profile_photos
            ext = os.path.splitext(file_path)[1].lower()
            new_filename = f"user_{self.user_id}{ext}"
            dest_path = os.path.join(get_profile_photo_dir(), new_filename)
            shutil.copy2(file_path, dest_path)

            # Simpan ke database
            save_user_photo(self.user_id, new_filename)

            # Refresh tampilan
            self._load_photo()
            self.photo_updated.emit()

            self._show_toast("✅ Foto profil berhasil diperbarui!")

        except Exception as e:
            self._show_toast(f"❌ Gagal: {str(e)}", success=False)

    def remove_photo(self):
        """Hapus foto profil."""
        # Hapus file fisik
        photo_path = get_user_photo_path(self.user_id)
        if photo_path and os.path.exists(photo_path):
            try:
                os.remove(photo_path)
            except Exception:
                pass

        # Kosongkan di database
        save_user_photo(self.user_id, "")

        # Refresh
        self._load_photo()
        self.photo_updated.emit()
        self._show_toast("✅ Foto profil dihapus.")
