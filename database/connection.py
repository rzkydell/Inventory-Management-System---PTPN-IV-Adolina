import sqlite3
import os
import sys
from datetime import datetime


def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_connection():
    base_path = get_base_path()

    db_path = os.path.join(base_path, "database", "management_barang.db")

    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Inisialisasi Tabel Audit Log
        conn.execute("""
            CREATE TABLE IF NOT EXISTS log_aktivitas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                waktu DATETIME NOT NULL,
                user TEXT NOT NULL DEFAULT 'Admin',
                aktivitas TEXT NOT NULL
            )
        """)
        conn.commit()
        
        # Tambahkan kolom keterangan jika belum ada untuk audit trail
        try:
            conn.execute("ALTER TABLE transaksi ADD COLUMN keterangan TEXT DEFAULT '-'")
            conn.commit()
        except sqlite3.OperationalError:
            pass # Kolom sudah ada
        
        return conn

    except sqlite3.Error as e:
        print(f"Gagal menyambung ke database: {e}")
        return None

def catat_log(aktivitas_teks):
    """Fungsi helper untuk mencatat riwayat aktivitas pengguna/Sistem."""
    try:
        conn = get_connection()
        if conn:
            waktu_skrg = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("INSERT INTO log_aktivitas (waktu, aktivitas) VALUES (?, ?)", (waktu_skrg, aktivitas_teks))
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"Gagal mencatat log: {e}")