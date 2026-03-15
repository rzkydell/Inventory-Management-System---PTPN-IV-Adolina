import os
import sqlite3
import sys
from barcode import Code128
from barcode.writer import ImageWriter
from database.connection import get_connection

def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        # Assuming this is in utils/barcode_utils.py, root is one level up
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def generate_barcode_image(code, barcode_dir):
    try:
        font_path = get_resource_path("assets/font/Apple.ttf")
        options = {
            'font_path': font_path, 
            'font_size': 10, 
            'text_distance': 4.0, 
            'module_height': 15.0, 
            'center_text': True
        }
        clean = "".join(c for c in str(code) if c.isalnum() or c in (" ", "_")).replace(" ", "_")
        file_path = os.path.join(barcode_dir, clean)
        with open(f"{file_path}.png", "wb") as f:
            Code128(str(code), writer=ImageWriter()).write(f, options=options)
        return True
    except Exception as e:
        print(f"Generate Barcode Error: {e}")
        return False

def sync_barcodes():
    """
    Sinkronisasi folder barcode dengan database:
    1. Buat folder jika belum ada.
    2. Tambah file barcode yang ada di DB tapi tidak ada di folder.
    3. Hapus file barcode yang tidak ada di DB.
    """
    if getattr(sys, 'frozen', False):
        root_dir = os.path.dirname(sys.executable)
    else:
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    barcode_dir = os.path.join(root_dir, "barcode")
    if not os.path.exists(barcode_dir):
        os.makedirs(barcode_dir)

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT barcode FROM barang_baru")
        db_barcodes = {str(row[0]) for row in cursor.fetchall()}
        conn.close()

        # 1. Clean filename (similar logic to MasterBarangPage)
        def clean_name(code):
            return "".join(c for c in str(code) if c.isalnum() or c in (" ", "_")).replace(" ", "_")

        db_filenames = {f"{clean_name(b)}.png" for b in db_barcodes}

        # 2. Get existing files
        existing_files = {f for f in os.listdir(barcode_dir) if f.endswith(".png")}

        # 3. Action: Delete orphaned files
        for f in existing_files:
            if f not in db_filenames:
                try: os.remove(os.path.join(barcode_dir, f))
                except Exception as e: print(f"Delete Orphan File Error: {e}")

        # 4. Action: Generate missing barcodes
        for b in db_barcodes:
            fname = f"{clean_name(b)}.png"
            if fname not in existing_files:
                generate_barcode_image(b, barcode_dir)

        print(f"Sync Barcode Success: {len(db_barcodes)} items synced.")
        return True
    except Exception as e:
        print(f"Sync Barcode Error: {e}")
        return False
