# 📦 Inventory Management System - PTPN IV Adolina

Sistem Manajemen Inventaris modern yang dirancang khusus untuk **PTPN IV Kebun Adolina**. Dibangun dengan antarmuka premium menggunakan PySide6, dilengkapi barcode scanner terintegrasi, sistem pelaporan, dan kontrol akses berbasis peran (Role-Based Access Control).

---

## 🚀 Fitur Utama

- **💎 UI/UX Premium:** Antarmuka modern dan profesional berbasis PySide6 dengan desain clean, shadow effect, dan navigasi sidebar responsif.
- **🛡️ Role-Based Access Control:**
  - **Super Admin** — Akses penuh ke seluruh fitur CRUD, pengaturan sistem, backup/restore database.
  - **User (Monitoring)** — Hanya dapat memantau Dashboard, melihat Laporan, dan Log Aktivitas.
  - Pendaftaran akun baru otomatis menjadi role **User** (monitoring only).
- **📦 Master Barang:** Kelola data inventaris lengkap dengan pencarian, filter kategori, bulk update, dan import CSV.
- **📥📤 Transaksi Masuk & Keluar:** Pencatatan pengadaan dan distribusi barang dengan riwayat stok otomatis.
- **⚖️ Audit Stok Opname:** Verifikasi fisik barang secara periodik untuk memastikan keakuratan data.
- **📊 Dashboard Analitik:**
  - KPI Card (Total Inventaris, Stok Kritis, Transaksi Harian)
  - Grafik tren aktivitas (7/30 hari & 1 tahun)
  - Distribusi stok per Kategori dan RAK
  - Prediksi AI barang yang akan habis dalam < 7 hari (Regresi Linier)
  - Monitor stok kritis real-time
- **🖨️ Sistem Barcode:**
  - Pembuatan barcode otomatis untuk item baru
  - Cetak barcode selektif ke layout PDF profesional
  - Sinkronisasi otomatis antara database dan folder lokal
- **📷 Scanner Kamera:** Scan barcode melalui kamera IP Smartphone (nirkabel via Wi-Fi)
- **📑 Log Aktivitas:** Rekam jejak lengkap setiap transaksi dan perubahan dalam sistem
- **💾 Backup & Restore:** Cadangkan dan pulihkan database dengan mudah
- **📈 Laporan Excel:** Ekspor data transaksi ke format Microsoft Excel (.xlsx)
- **🔔 Notifikasi Tray:** Peringatan stok kritis melalui Windows System Tray

---

## 🛠️ Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| **Bahasa** | Python 3.10+ |
| **GUI Framework** | PySide6 (Qt for Python) |
| **Database** | SQLite3 |
| **Image Processing** | OpenCV, PyZbar, Pillow |
| **Barcode Generator** | python-barcode |
| **Grafik & Analitik** | Matplotlib |
| **Reporting** | ReportLab (PDF), openpyxl (Excel) |

---

## 📁 Struktur Proyek

```
management_barang/
├── main.py                  # Entry point aplikasi
├── config.json              # Konfigurasi scanner kamera IP
├── requirements.txt         # Dependensi Python
├── assets/                  # Aset gambar dan ikon
├── barcode/                 # Barcode yang di-generate
├── label_masuk/             # Label cetak masuk
├── database/
│   ├── connection.py        # Koneksi DB, migrasi, dan logging
│   └── management_barang.db # Database SQLite
├── models/
│   ├── user_model.py        # Autentikasi & registrasi (dengan role)
│   ├── barang_model.py      # CRUD data barang
│   ├── transaksi_model.py   # Transaksi masuk/keluar
│   └── pendukung_model.py   # Kategori & lokasi penyimpanan
├── ui/
│   ├── login_window.py      # Halaman login
│   ├── register_window.py   # Halaman registrasi (role: user)
│   ├── dashboard_window.py  # Shell utama + sidebar + role-based menu
│   ├── dashboard_page.py    # Dashboard analitik & KPI
│   ├── master_barang_page.py
│   ├── master_pendukung_page.py
│   ├── barang_form_page.py
│   ├── barang_masuk_page.py
│   ├── barang_keluar_page.py
│   ├── audit_stok_page.py
│   ├── laporan_page.py
│   ├── pengaturan_page.py
│   └── log_aktivitas_page.py
└── utils/
    ├── barcode_utils.py     # Utilitas barcode
    ├── config_manager.py    # Pengelolaan konfigurasi
    └── path_helper.py       # Helper path untuk mode dev & EXE
```

---

## 🔧 Instalasi

1. **Clone repositori:**
   ```bash
   git clone https://github.com/rzkydell/Inventory-Management-System---PTPN-IV-Adolina.git
   cd Inventory-Management-System---PTPN-IV-Adolina
   ```

2. **Buat Virtual Environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   # source venv/bin/activate   # Linux/Mac
   ```

3. **Install Dependensi:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🖥️ Menjalankan Aplikasi

```bash
python main.py
```

### Akses Default

| Role | Keterangan |
|------|------------|
| **Super Admin** | User pertama yang terdaftar di database secara otomatis menjadi Super Admin |
| **User** | Setiap akun baru yang dibuat via halaman Daftar akan menjadi User (monitoring only) |

### Hak Akses per Role

| Menu | Super Admin | User |
|------|:-----------:|:----:|
| Dashboard (KPI, Grafik, Monitor) | ✅ | ✅ |
| Master Data (Barang, Kategori, Lokasi) | ✅ | ❌ |
| Barang Masuk / Keluar | ✅ | ❌ |
| Audit Stok Opname | ✅ | ❌ |
| Laporan & Ekspor Excel | ✅ | ✅ |
| Log Aktivitas | ✅ | ✅ |
| Pengaturan & Backup/Restore | ✅ | ❌ |

---

## 🧑‍💻 Author

Dibuat oleh **[rzkydell](https://github.com/rzkydell)**

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.
