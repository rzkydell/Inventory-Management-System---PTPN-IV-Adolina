import sys
import os
import ctypes
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.login_window import LoginWindow
from utils.path_helper import get_resource_path, get_root_dir

def main():
    # --- OPTIMASI PySide6 ---
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    # Qt6 handles HighDPI scaling natively, so we remove the deprecated Qt.AA flags.

    # Trik agar ikon muncul di Taskbar Windows (AppUserModelID)
    try:
        myappid = 'ptpn4.inventory.adolina.v1' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        print(f"AppID Error: {e}")

    app = QApplication(sys.argv)

    # Set Global Font (Professional Typography)
    try:
        from PySide6.QtGui import QFont
        font = QFont("Segoe UI", 10)
        app.setFont(font)
    except Exception as e: print(f"Font Error: {e}")

    # Path ke icon aplikasi
    app_icon_path = os.path.join(get_root_dir(), "assets", "images", "Logo PTPN IV.png") # Menggunakan PNG agar transparansi bagus
    
    if os.path.exists(app_icon_path):
        app_icon = QIcon(app_icon_path)
        app.setWindowIcon(app_icon) 
    else:
        print(f"Peringatan: File ikon tidak ditemukan di {app_icon_path}")

    # Inisialisasi Jendela Login
    window = LoginWindow()
    
    if os.path.exists(app_icon_path):
        window.setWindowIcon(QIcon(app_icon_path))
    
    window.show()
    code = app.exec()
    
    # --- AUTO BACKUP DATABASE PADA SAAT TUTUP APLIKASI ---
    try:
        import shutil
        import datetime
        db_path = os.path.join(get_root_dir(), "database", "management_barang.db")
        if os.path.exists(db_path):
            backup_dir = os.path.join(get_root_dir(), "database", "backups")
            os.makedirs(backup_dir, exist_ok=True)
            waktu = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(backup_dir, f"backup_{waktu}.db")
            shutil.copy2(db_path, backup_path)
            
            # Keep only the last 7 backups to save space
            backups = sorted([os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.startswith("backup_") and f.endswith(".db")])
            if len(backups) > 7:
                for old_db in backups[:-7]:
                    try:
                        os.remove(old_db)
                    except Exception as e: print(f"Cleanup Backup Error: {e}")
    except Exception as e:
        print(f"Gagal mem-backup database: {e}")

    sys.exit(code)

if __name__ == "__main__":
    main()