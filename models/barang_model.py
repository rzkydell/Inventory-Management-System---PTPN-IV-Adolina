import sqlite3
from database.connection import get_connection

class BarangModel:
    @staticmethod
    def get_all_with_details():
        try:
            conn = get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT b.*, k.nama_kategori, l.nama_lokasi 
                FROM barang_baru b 
                LEFT JOIN kategori k ON b.id_kategori = k.id_kategori 
                LEFT JOIN lokasi l ON b.id_lokasi = l.id_lokasi 
                ORDER BY b.id_barang ASC
            """)
            rows = cursor.fetchall()
            conn.close()
            return rows
        except Exception as e:
            print(f"BarangModel.get_all_with_details Error: {e}")
            return []

    @staticmethod
    def get_by_id(id_barang):
        try:
            conn = get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT b.*, k.nama_kategori, l.nama_lokasi as nama_slot
                FROM barang_baru b 
                LEFT JOIN kategori k ON b.id_kategori = k.id_kategori
                LEFT JOIN lokasi l ON b.id_lokasi = l.id_lokasi 
                WHERE b.id_barang = ?
            """, (id_barang,))
            row = cursor.fetchone()
            conn.close()
            return row
        except Exception as e:
            print(f"BarangModel.get_by_id Error: {e}")
            return None

    @staticmethod
    def get_by_barcode(barcode):
        try:
            conn = get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT b.*, k.nama_kategori, l.nama_lokasi as nama_slot
                FROM barang_baru b 
                LEFT JOIN kategori k ON b.id_kategori = k.id_kategori
                LEFT JOIN lokasi l ON b.id_lokasi = l.id_lokasi 
                WHERE b.barcode = ?
            """, (barcode,))
            rows = cursor.fetchall()
            conn.close()
            return rows
        except Exception as e:
            print(f"BarangModel.get_by_barcode Error: {e}")
            return []

    @staticmethod
    def add(barcode, nama, rak, id_kat, id_lok, satuan, stok_min):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO barang_baru (barcode, nama_barang, rak, id_kategori, id_lokasi, satuan, stok_minimum, stok)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """, (barcode, nama, rak, id_kat, id_lok, satuan, stok_min))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"BarangModel.add Error: {e}")
            return False

    @staticmethod
    def update(id_barang, barcode, nama, rak, id_kat, id_lok, satuan, stok_min):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE barang_baru SET barcode=?, nama_barang=?, rak=?, id_kategori=?, 
                id_lokasi=?, satuan=?, stok_minimum=? WHERE id_barang=?
            """, (barcode, nama, rak, id_kat, id_lok, satuan, stok_min, id_barang))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"BarangModel.update Error: {e}")
            return False

    @staticmethod
    def update_stok(id_barang, stok_baru):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE barang_baru SET stok = ? WHERE id_barang = ?", (stok_baru, id_barang))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"BarangModel.update_stok Error: {e}")
            return False

    @staticmethod
    def delete(id_barang):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM barang_baru WHERE id_barang=?", (id_barang,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"BarangModel.delete Error: {e}")
            return False

    @staticmethod
    def bulk_update_kategori(ids, id_kat):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            for bid in ids:
                cursor.execute("UPDATE barang_baru SET id_kategori = ? WHERE id_barang = ?", (id_kat, bid))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"BarangModel.bulk_update_kategori Error: {e}")
            return False

    @staticmethod
    def bulk_update_lokasi(ids, id_lok):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            for bid in ids:
                cursor.execute("UPDATE barang_baru SET id_lokasi = ? WHERE id_barang = ?", (id_lok, bid))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"BarangModel.bulk_update_lokasi Error: {e}")
            return False

    @staticmethod
    def get_total_count():
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM barang_baru")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0

    @staticmethod
    def get_kritis_count():
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM barang_baru WHERE stok <= stok_minimum")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0

    @staticmethod
    def get_kritis_data(category=None, limit=20):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            query = """
                SELECT b.barcode, b.nama_barang, COALESCE(k.nama_kategori, '-'), b.rak, COALESCE(l.nama_lokasi, '-'), b.stok 
                FROM barang_baru b 
                LEFT JOIN kategori k ON b.id_kategori = k.id_kategori 
                LEFT JOIN lokasi l ON b.id_lokasi = l.id_lokasi 
                WHERE b.stok <= b.stok_minimum
            """
            params = []
            if category and category != "Semua Kategori":
                query += " AND k.nama_kategori = ?"
                params.append(category)
            query += " ORDER BY b.stok ASC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            return rows
        except:
            return []

    @staticmethod
    def get_distribusi_kategori():
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT k.nama_kategori, SUM(b.stok) 
                FROM barang_baru b 
                JOIN kategori k ON b.id_kategori = k.id_kategori 
                GROUP BY k.id_kategori
            """)
            data = cursor.fetchall()
            conn.close()
            return data
        except:
            return []

    @staticmethod
    def get_distribusi_rak():
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT rak, SUM(stok) 
                FROM barang_baru 
                GROUP BY rak
            """)
            data = cursor.fetchall()
            conn.close()
            return data
        except:
            return []

    @staticmethod
    def generate_next_barcode():
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(id_barang) FROM barang_baru")
            res = cursor.fetchone()[0] or 0
            conn.close()
            return f"BRG{(res + 1):05d}"
        except:
            return "BRG-ERR"
