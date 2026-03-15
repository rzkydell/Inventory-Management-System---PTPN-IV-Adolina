"""
Modul utilitas path terpusat.
Menyediakan fungsi untuk mendapatkan path resource dan root directory,
baik saat berjalan sebagai skrip .py maupun sebagai bundle .exe (PyInstaller).
"""
import os
import sys


def get_resource_path(relative_path):
    """Mendapatkan path absolut ke resource, kompatibel dengan PyInstaller."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def get_root_dir():
    """Mendapatkan direktori root aplikasi (tempat .exe atau folder proyek)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
