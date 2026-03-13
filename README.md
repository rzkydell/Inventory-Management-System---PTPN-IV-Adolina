# 📦 Inventory Management System - PTPN IV Adolina

A modern, professional, and efficient Inventory Management System designed for **PTPN IV Adolina**. This application features a premium UI/UX, integrated barcode scanning, and PDF barcode generation.

---

## 🚀 Key Features

- **💎 Premium UI/UX:** Built with PySide6, featuring a modern, clean, and professional interface inspired by glassmorphism and modern design trends.
- **📦 Master Barang Management:** Full CRUD operations for inventory items with advanced search and filtering.
- **📊 Stock Audit:** Real-time monitoring of stock levels with visual alerts for low stock.
- **🖨️ Barcode System:**
    - Automatic barcode generation for new items.
    - Printing specific (selective) barcodes to professional PDF layouts.
    - Automatic folder synchronization between the database and local assets.
- **📷 Camera Scanner:** Integrated barcode scanning using your computer's camera.
- **📑 Activity Logs:** Detailed tracking of every transaction and system modification.
- **🛡️ Secure Access:** Robust login and registration system.

---

## 🛠️ Tech Stack

- **Core:** Python 3.10+
- **GUI Framework:** PySide6 (Qt for Python)
- **Database:** SQLite3
- **Image Processing:** OpenCV, PyZbar, Pillow
- **Barcode:** Python-Barcode
- **Reporting:** ReportLab (PDF Generation)

---

## 🔧 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/rzkydell/management_barang.git
   cd management_barang
   ```

2. **Setup Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## 🖥️ Running the Application

To start the application, simply run:
```bash
python main.py
```

---

## 🧑‍💻 Author

Created with Passion by **[rzkydell](https://github.com/rzkydell)**

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.
