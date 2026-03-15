import sqlite3
from database.connection import get_connection

class TransaksiModel:
    @staticmethod
    def record_transaksi(id_barang, jenis, stok_sebelum, stok_sesudah, metode, tanggal, keterangan, sisa_qty=None):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            if sisa_qty is not None:
                cursor.execute("""
                    INSERT INTO transaksi (id_barang, jenis, stok_sebelum, stok_sesudah, metode, sisa_qty, tanggal, keterangan) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (id_barang, jenis, stok_sebelum, stok_sesudah, metode, sisa_qty, tanggal, keterangan))
            else:
                cursor.execute("""
                    INSERT INTO transaksi (id_barang, jenis, stok_sebelum, stok_sesudah, metode, tanggal, keterangan) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (id_barang, jenis, stok_sebelum, stok_sesudah, metode, tanggal, keterangan))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"TransaksiModel.record_transaksi Error: {e}")
            return False

    @staticmethod
    def get_daily_count(jenis, tanggal_prefix):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM transaksi WHERE jenis=? AND tanggal LIKE ?", (jenis, f"{tanggal_prefix}%"))
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0

    @staticmethod
    def get_history_paged(jenis, checkpoint, limit=200):
        try:
            conn = get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Logic varies slightly between MASUK and KELUAR based on your existing queries
            if jenis == 'MASUK':
                cursor.execute("""
                    SELECT t.tanggal, b.barcode, b.nama_barang, b.rak, l.nama_lokasi as slot,
                           (t.stok_sesudah - t.stok_sebelum) as qty, t.stok_sebelum, t.stok_sesudah, t.metode, t.keterangan
                    FROM transaksi t 
                    JOIN barang_baru b ON t.id_barang = b.id_barang 
                    LEFT JOIN lokasi l ON b.id_lokasi = l.id_lokasi
                    WHERE t.jenis = 'MASUK' AND t.tanggal > ? ORDER BY t.tanggal DESC LIMIT ?
                """, (checkpoint, limit))
            else:
                cursor.execute("""
                    SELECT t.tanggal, b.barcode, b.nama_barang, b.rak, l.nama_lokasi as slot,
                           (t.stok_sebelum - t.stok_sesudah) as qty, t.stok_sebelum, t.stok_sesudah, t.keterangan
                    FROM transaksi t 
                    JOIN barang_baru b ON t.id_barang = b.id_barang 
                    LEFT JOIN lokasi l ON b.id_lokasi = l.id_lokasi
                    WHERE t.jenis = 'KELUAR' AND t.tanggal > ? ORDER BY t.tanggal DESC LIMIT ?
                """, (checkpoint, limit))
                
            rows = cursor.fetchall()
            conn.close()
            return rows
        except:
            return []

    @staticmethod
    def get_suplier_list():
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT keterangan FROM transaksi WHERE jenis='MASUK' AND keterangan != '-' AND keterangan IS NOT NULL")
            results = [r[0] for r in cursor.fetchall() if r[0].strip()]
            conn.close()
            return results
        except:
            return []

    @staticmethod
    def get_penerima_list():
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT keterangan FROM transaksi WHERE jenis='KELUAR' AND keterangan != '-' AND keterangan IS NOT NULL")
            results = [r[0] for r in cursor.fetchall() if r[0].strip()]
            conn.close()
            return results
        except:
            return []

    @staticmethod
    def get_fifo_batches(barcode):
        try:
            conn = get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.id_transaksi, t.id_barang, t.tanggal, t.sisa_qty, 
                       b.nama_barang, b.rak, l.nama_lokasi as slot
                FROM transaksi t
                JOIN barang_baru b ON t.id_barang = b.id_barang
                LEFT JOIN lokasi l ON b.id_lokasi = l.id_lokasi
                WHERE b.barcode = ? AND t.jenis = 'MASUK' AND t.sisa_qty > 0
                ORDER BY t.tanggal ASC
            """, (barcode,))
            rows = cursor.fetchall()
            conn.close()
            return rows
        except:
            return []

    @staticmethod
    def get_total_sisa_qty(barcode):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(t.sisa_qty) 
                FROM transaksi t JOIN barang_baru b ON t.id_barang = b.id_barang
                WHERE b.barcode = ? AND t.jenis = 'MASUK' AND t.sisa_qty > 0
            """, (barcode,))
            res = cursor.fetchone()[0]
            conn.close()
            return res if res is not None else 0
        except:
            return 0

    @staticmethod
    def update_batch_sisa(id_transaksi, qty_reduction):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE transaksi SET sisa_qty = sisa_qty - ? WHERE id_transaksi = ?", (qty_reduction, id_transaksi))
            conn.commit()
            conn.close()
            return True
        except:
            return False

    @staticmethod
    def get_recent_out_transactions(days=30):
        from datetime import datetime, timedelta
        try:
            conn = get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            date_limit = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT t.id_barang, b.nama_barang, b.stok, t.tanggal, t.stok_sebelum, t.stok_sesudah 
                FROM transaksi t
                JOIN barang_baru b ON t.id_barang = b.id_barang
                WHERE t.jenis = 'KELUAR' AND t.tanggal >= ?
                ORDER BY t.tanggal ASC
            """, (date_limit,))
            rows = cursor.fetchall()
            conn.close()
            return rows
        except:
            return []
