import sqlite3
from database.connection import get_connection

class PendukungModel:
    @staticmethod
    def get_all_kategori():
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id_kategori, nama_kategori FROM kategori ORDER BY nama_kategori ASC")
            rows = cursor.fetchall()
            conn.close()
            return rows
        except:
            return []

    @staticmethod
    def get_all_lokasi():
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id_lokasi, nama_lokasi FROM lokasi ORDER BY nama_lokasi ASC")
            rows = cursor.fetchall()
            conn.close()
            return rows
        except:
            return []

    @staticmethod
    def add_kategori(nama):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO kategori (nama_kategori) VALUES (?)", (nama,))
            conn.commit()
            conn.close()
            return True
        except:
            return False

    @staticmethod
    def add_lokasi(nama):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO lokasi (nama_lokasi) VALUES (?)", (nama,))
            conn.commit()
            conn.close()
            return True
        except:
            return False

    @staticmethod
    def update_kategori(id_kat, nama_baru):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE kategori SET nama_kategori = ? WHERE id_kategori = ?", (nama_baru, id_kat))
            conn.commit()
            conn.close()
            return True
        except:
            return False

    @staticmethod
    def delete_kategori(id_kat):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM kategori WHERE id_kategori = ?", (id_kat,))
            conn.commit()
            conn.close()
            return True
        except:
            return False

    @staticmethod
    def update_lokasi(id_lok, nama_baru):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE lokasi SET nama_lokasi = ? WHERE id_lokasi = ?", (nama_baru, id_lok))
            conn.commit()
            conn.close()
            return True
        except:
            return False

    @staticmethod
    def delete_lokasi(id_lok):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM lokasi WHERE id_lokasi = ?", (id_lok,))
            conn.commit()
            conn.close()
            return True
        except:
            return False
