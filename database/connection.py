import sqlite3
import os
import sys
import logging
from datetime import datetime
from contextlib import contextmanager

# Setup module-level logger
logger = logging.getLogger("InventoryApp")


def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_connection():
    """Mendapatkan koneksi database. Caller bertanggung jawab menutup koneksi."""
    base_path = get_base_path()
    db_path = os.path.join(base_path, "database", "management_barang.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS log_aktivitas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                waktu DATETIME NOT NULL,
                user TEXT NOT NULL DEFAULT 'Admin',
                aktivitas TEXT NOT NULL
            )
        """)
        conn.commit()
        
        try:
            conn.execute("ALTER TABLE transaksi ADD COLUMN keterangan TEXT DEFAULT '-'")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Kolom sudah ada

        # Migrasi: Tambah kolom role pada tabel users jika belum ada
        try:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
            conn.commit()
            # Setelah kolom berhasil ditambahkan, set user pertama sebagai super_admin
            conn.execute("UPDATE users SET role='super_admin' WHERE id_user = (SELECT MIN(id_user) FROM users)")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Kolom sudah ada

        # Migrasi: Tambah kolom profile_photo pada tabel users
        try:
            conn.execute("ALTER TABLE users ADD COLUMN profile_photo TEXT DEFAULT ''")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Kolom sudah ada

        # Migrasi: Tambah kolom nama pada tabel users
        try:
            conn.execute("ALTER TABLE users ADD COLUMN nama TEXT DEFAULT ''")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Kolom sudah ada
        
        return conn

    except sqlite3.Error as e:
        logger.error(f"Gagal menyambung ke database: {e}")
        return None


@contextmanager
def safe_connection():
    """Context manager untuk koneksi database yang aman — otomatis ditutup."""
    conn = get_connection()
    try:
        yield conn
    finally:
        if conn:
            conn.close()


def catat_log(aktivitas_teks, user="Admin"):
    """Fungsi helper untuk mencatat riwayat aktivitas pengguna/Sistem."""
    conn = None
    try:
        conn = get_connection()
        if conn:
            waktu_skrg = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("INSERT INTO log_aktivitas (waktu, user, aktivitas) VALUES (?, ?, ?)", (waktu_skrg, user, aktivitas_teks))
            conn.commit()
    except Exception as e:
        logger.error(f"Gagal mencatat log: {e}")
    finally:
        if conn:
            conn.close()