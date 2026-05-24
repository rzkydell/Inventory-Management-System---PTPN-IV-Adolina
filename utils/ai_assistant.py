"""
Modul AI Assistant — Otak dari fitur Asisten Cerdas Inventaris.
Menggunakan Google Gemini API untuk menerjemahkan pertanyaan bahasa Indonesia
menjadi query SQL (read-only) terhadap database management_barang.db.

Keamanan:
- Hanya operasi SELECT yang diizinkan (read-only).
- System prompt dikunci agar AI hanya menjawab seputar inventaris.
- Tidak ada data sensitif yang dikirim ke API — hanya struktur tabel & hasil query.
"""

import sqlite3
import json
import re
import time
import urllib.request
import urllib.error
import logging
from database.connection import get_connection
from utils.config_manager import get_gemini_api_key

logger = logging.getLogger("InventoryApp.AI")

# ============================================================
# KONFIGURASI
# ============================================================
# GEMINI_API_KEY kini diambil dinamis melalui config_manager.get_gemini_api_key()

# Daftar model prioritas sesuai dengan ketersediaan API key Anda
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash",
]

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # detik — delay awal sebelum retry

# ============================================================
# SKEMA DATABASE (Diberikan ke AI agar paham struktur tabel)
# ============================================================
DATABASE_SCHEMA = """
-- Tabel Users: Menyimpan data akun pengguna sistem
CREATE TABLE users (
    id_user INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,  -- JANGAN PERNAH TAMPILKAN KOLOM INI ATAU KETAHUI KONTENNYA
    role TEXT NOT NULL DEFAULT 'user',  -- 'super_admin' atau 'user'
    nama TEXT,  -- Nama Lengkap Tampilan Pengguna (Boleh dibagikan jika ditanya)
    profile_photo TEXT  -- Path/Nama file foto profil
);

-- Tabel Kategori: Klasifikasi jenis barang
CREATE TABLE kategori (
    id_kategori INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_kategori TEXT NOT NULL UNIQUE
);

-- Tabel Lokasi: Lokasi penyimpanan/slot gudang
CREATE TABLE lokasi (
    id_lokasi INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_lokasi TEXT NOT NULL UNIQUE
);

-- Tabel Barang: Data utama inventaris barang
CREATE TABLE barang_baru (
    id_barang INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode TEXT NOT NULL,
    nama_barang TEXT NOT NULL,
    id_kategori INTEGER NOT NULL REFERENCES kategori(id_kategori),
    id_lokasi INTEGER NOT NULL REFERENCES lokasi(id_lokasi),
    satuan TEXT,
    stok INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    rak TEXT,
    stok_minimum INTEGER DEFAULT 5,
    UNIQUE(barcode, id_lokasi)
);

-- Tabel Transaksi: Riwayat barang masuk dan keluar
CREATE TABLE transaksi (
    id_transaksi INTEGER PRIMARY KEY AUTOINCREMENT,
    id_barang INTEGER NOT NULL REFERENCES barang_baru(id_barang),
    jenis TEXT NOT NULL,  -- 'MASUK' atau 'KELUAR'
    stok_sebelum INTEGER NOT NULL,
    stok_sesudah INTEGER NOT NULL,
    metode TEXT,  -- metode transaksi (misal: 'Manual', 'Barcode')
    sisa_qty INTEGER,  -- sisa quantity batch FIFO (hanya untuk MASUK)
    tanggal DATETIME DEFAULT CURRENT_TIMESTAMP,
    keterangan TEXT DEFAULT '-'  -- suplier (MASUK) atau penerima (KELUAR)
);

-- Tabel Log Aktivitas: Rekam jejak aksi pengguna
CREATE TABLE log_aktivitas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    waktu DATETIME NOT NULL,
    user TEXT NOT NULL DEFAULT 'Admin',
    aktivitas TEXT NOT NULL
);
"""

# ============================================================
# SYSTEM PROMPT (Instruksi mutlak untuk AI)
# ============================================================
SYSTEM_PROMPT = f"""Kamu adalah **Asisten AI Inventaris PTPN IV Kebun Adolina**.

ATURAN MUTLAK YANG TIDAK BOLEH DILANGGAR:
1. Kamu HANYA boleh membahas topik seputar manajemen inventaris/gudang berdasarkan database ini. Selalu hit/query database SQLite lokal kita untuk mendapatkan fakta valid.
2. Jika pengguna bertanya di luar topik inventaris (resep masakan, politik, berita, coding, dll), TOLAK dengan sopan: "Maaf, saya hanya Asisten Inventaris PTPN IV. Saya hanya bisa membantu menganalisis data barang, transaksi, stok, dan informasi gudang lainnya."
3. **KERAHASIAAN & PRIVASI AKUN:** Kamu dilarang keras mengungkapkan, membocorkan, atau meng-query informasi akun sensitif seperti data hash password (kolom `password`) atau username login (kolom `username`) milik pengguna demi keamanan sistem. 
4. **NAMA USER YANG BOLEH DIBAGIKAN:** Kamu **DIPERBOLEHKAN** dan **DIIZINKAN** untuk memberitahu siapa saja **NAMA LENGKAP** (dari kolom `nama` di tabel `users`) dari pengguna yang terdaftar di sistem jika ditanya.
5. Kamu hanya boleh menghasilkan query SQL bertipe SELECT (read-only). DILARANG keras melakukan modifikasi database (INSERT, UPDATE, DELETE, DROP, ALTER, dll).
6. Jawab dalam Bahasa Indonesia yang profesional, ringkas, hangat, dan mudah dipahami.
7. Jika data tidak ditemukan, sampaikan dengan jelas bahwa tidak ada data yang cocok di database.
8. Format jawaban dengan rapi. Gunakan tabel teks jika menampilkan banyak baris data. Gunakan emoji secukupnya agar menarik.

SKEMA DATABASE YANG KAMU KELOLA:
{DATABASE_SCHEMA}

PANDUAN QUERY:
- Untuk mendapatkan nama kategori, JOIN tabel barang_baru dengan kategori.
- Untuk mendapatkan nama lokasi, JOIN tabel barang_baru dengan lokasi.
- Untuk menghitung qty masuk: (stok_sesudah - stok_sebelum) dari tabel transaksi WHERE jenis='MASUK'.
- Untuk menghitung qty keluar: (stok_sebelum - stok_sesudah) dari tabel transaksi WHERE jenis='KELUAR'.
- Kolom keterangan pada transaksi berisi nama suplier (jika MASUK) atau nama penerima (jika KELUAR).
- Barang kritis adalah barang yang stok-nya kurang dari atau sama dengan stok_minimum.

CARA KERJA:
- Jika pengguna bertanya hal yang membutuhkan data dari database, buatkan query SQL-nya terlebih dahulu.
- Bungkus query SQL dalam blok ```sql ... ```.
- Setelah kamu membuat query, sistem akan mengeksekusinya dan memberikan hasilnya kepadamu.
- Kemudian kamu rangkum hasilnya menjadi jawaban yang informatif dan mudah dibaca.
- Jika pertanyaan bisa dijawab langsung tanpa query (misal: penjelasan fitur), jawab langsung saja.
"""


def _is_select_only(sql: str) -> bool:
    """Validasi bahwa SQL hanya mengandung perintah SELECT (read-only)."""
    cleaned = sql.strip().upper()
    # Hapus komentar
    cleaned = re.sub(r'--.*$', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
    cleaned = cleaned.strip()

    forbidden = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE',
                 'REPLACE', 'TRUNCATE', 'ATTACH', 'DETACH', 'PRAGMA',
                 'VACUUM', 'REINDEX']
    for keyword in forbidden:
        # Periksa apakah keyword muncul sebagai kata utuh (bukan bagian dari nama kolom)
        if re.search(rf'\b{keyword}\b', cleaned):
            return False
    return cleaned.startswith('SELECT') or cleaned.startswith('WITH')


def _extract_sql_from_response(text: str) -> list:
    """Ekstrak semua blok SQL dari respons AI."""
    pattern = r'```sql\s*(.*?)\s*```'
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    return [m.strip() for m in matches if m.strip()]


def _execute_readonly_query(sql: str) -> tuple:
    """
    Eksekusi query SQL secara read-only terhadap database.
    Mengembalikan (columns, rows) atau (None, error_message).
    """
    if not _is_select_only(sql):
        return None, "⛔ Query ditolak: Hanya perintah SELECT yang diizinkan."

    conn = None
    try:
        conn = get_connection()
        if conn is None:
            return None, "❌ Gagal tersambung ke database."

        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []

        # Konversi Row objects ke list biasa
        result_rows = []
        for row in rows:
            if hasattr(row, 'keys'):
                result_rows.append([row[col] for col in columns])
            else:
                result_rows.append(list(row))

        return (columns, result_rows), None
    except sqlite3.Error as e:
        return None, f"❌ Error SQL: {str(e)}"
    except Exception as e:
        return None, f"❌ Error: {str(e)}"
    finally:
        if conn:
            conn.close()


def _format_query_result(columns: list, rows: list, max_rows: int = 50) -> str:
    """Format hasil query menjadi teks tabel yang mudah dibaca oleh AI."""
    if not rows:
        return "Tidak ada data yang ditemukan."

    total = len(rows)
    display_rows = rows[:max_rows]

    lines = []
    lines.append(f"Kolom: {', '.join(columns)}")
    lines.append(f"Jumlah baris: {total}" + (f" (menampilkan {max_rows} pertama)" if total > max_rows else ""))
    lines.append("")

    for i, row in enumerate(display_rows):
        row_str = " | ".join([str(val) if val is not None else "NULL" for val in row])
        lines.append(f"Baris {i + 1}: {row_str}")

    return "\n".join(lines)


def _call_gemini_api(messages: list) -> str:
    """
    Kirim permintaan ke Google Gemini API menggunakan urllib (tanpa dependency tambahan).
    Mendukung retry otomatis dan fallback ke model alternatif jika kuota habis.
    """
    payload = {
        "contents": messages,
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 4096,
            "thinkingConfig": {
                "thinkingBudget": 0
            }
        }
    }

    last_error_msg = ""

    for model_name in GEMINI_MODELS:
        current_api_key = get_gemini_api_key()
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={current_api_key}"

        for attempt in range(MAX_RETRIES):
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                api_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    result = json.loads(response.read().decode("utf-8"))

                # Ekstrak teks jawaban dari response Gemini
                # Gemini 2.5+ bisa mengembalikan 'thought' parts — kita ambil hanya 'text'
                candidates = result.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text_parts = []
                    for part in parts:
                        # Skip thought parts, ambil hanya text biasa
                        if "thought" in part and part.get("thought"):
                            continue
                        if "text" in part and part["text"].strip():
                            text_parts.append(part["text"])
                    if text_parts:
                        return "\n".join(text_parts)

                return "Maaf, saya tidak mendapatkan respons dari server AI."

            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8", errors="replace")
                logger.error(f"Gemini API ({model_name}) HTTP Error {e.code} [attempt {attempt+1}]: {error_body[:200]}")

                if e.code == 429:
                    # Rate limit — retry dengan backoff, lalu coba model berikutnya
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.info(f"Rate limited pada {model_name}. Retry dalam {delay}s...")
                    time.sleep(delay)
                    last_error_msg = (
                        "⚠️ **Batas Permintaan Terlampaui (Error 429 - Quota Exceeded)**\n\n"
                        "Kuota harian gratis untuk API Key Anda saat ini telah habis.\n\n"
                        "👉 **Solusi:** Silakan buat API Key baru secara gratis di **Google AI Studio** dan simpan kunci baru tersebut di halaman **Pengaturan**."
                    )
                    continue
                elif e.code == 403:
                    last_error_msg = (
                        "⚠️ **Akses Ditolak / API Key Bocor (Error 403)**\n\n"
                        "Kunci API Anda tidak valid atau telah **diblokir secara permanen oleh sistem keamanan Google karena terdeteksi bocor** secara publik.\n\n"
                        "👉 **Solusi:** Buka halaman **Pengaturan** di sidebar kiri Anda, buat API Key baru secara gratis dari **Google AI Studio**, lalu masukkan dan simpan di sana."
                    )
                    break  # Tidak perlu retry, API key ditolak
                elif e.code == 404:
                    last_error_msg = (
                        f"⚠️ **Model Tidak Ditemukan (Error 404)**\n\n"
                        f"Model `{model_name}` tidak ditemukan atau tidak didukung pada region/API Key Anda saat ini.\n\n"
                        f"👉 **Solusi:** Pastikan jenis model didukung secara resmi di region Anda."
                    )
                    break
                else:
                    last_error_msg = f"⚠️ **Error Server AI (HTTP {e.code})**\n\nGoogle mengembalikan kesalahan: {e.reason or 'Internal Error'}. Silakan coba lagi nanti."
                    break

            except urllib.error.URLError as e:
                logger.error(f"Gemini API URL Error: {e.reason}")
                last_error_msg = (
                    "⚠️ **Tidak Ada Koneksi Internet**\n\n"
                    "Gagal menghubungkan ke server Google Gemini. Periksa kembali koneksi internet komputer/laptop Anda lalu coba lagi."
                )
                break  # Tidak perlu retry jika tidak ada koneksi

            except Exception as e:
                logger.error(f"Gemini API Error: {e}")
                last_error_msg = f"⚠️ **Terjadi Kesalahan Teknis**\n\nDetail Error: {str(e)}"
                break

        # Jika semua retry gagal untuk model ini, coba model berikutnya
        logger.info(f"Model {model_name} gagal, mencoba model berikutnya...")

    return last_error_msg or "⚠️ Semua model AI sedang tidak tersedia saat ini. Silakan coba beberapa saat lagi."


class AIAssistant:
    """
    Kelas utama AI Assistant.
    Mengelola riwayat percakapan dan alur Text-to-SQL.
    """

    def __init__(self):
        self.conversation_history = []

    def clear_history(self):
        """Reset riwayat percakapan."""
        self.conversation_history = []

    def ask(self, user_question: str) -> str:
        """
        Proses pertanyaan pengguna dengan alur:
        1. Kirim pertanyaan ke Gemini.
        2. Jika respons berisi SQL, eksekusi secara read-only.
        3. Kirim hasil query kembali ke Gemini untuk dirangkum.
        4. Kembalikan jawaban akhir.
        """
        if not user_question.strip():
            return "Silakan ketikkan pertanyaan Anda."

        # Tambah pesan user ke history
        self.conversation_history.append({
            "role": "user",
            "parts": [{"text": user_question}]
        })

        # --- Langkah 1: Kirim ke Gemini ---
        ai_response = _call_gemini_api(self.conversation_history)

        # --- Langkah 2: Cek apakah ada SQL dalam respons ---
        sql_queries = _extract_sql_from_response(ai_response)

        if sql_queries:
            # Eksekusi setiap query dan kumpulkan hasilnya
            all_results = []
            for sql in sql_queries:
                result, error = _execute_readonly_query(sql)
                if error:
                    all_results.append(f"Query: {sql}\nHasil: {error}")
                else:
                    columns, rows = result
                    formatted = _format_query_result(columns, rows)
                    all_results.append(f"Query: {sql}\nHasil:\n{formatted}")

            # Simpan respons AI (yang berisi SQL) ke history
            self.conversation_history.append({
                "role": "model",
                "parts": [{"text": ai_response}]
            })

            # --- Langkah 3: Kirim hasil query kembali ke Gemini untuk dirangkum ---
            result_text = "\n\n".join(all_results)
            followup_message = (
                f"Berikut hasil eksekusi query yang kamu buat:\n\n{result_text}\n\n"
                f"Sekarang, rangkum dan jelaskan hasil data di atas dalam Bahasa Indonesia "
                f"yang mudah dipahami oleh pengguna. Berikan insight atau analisis jika relevan. "
                f"Format dengan rapi dan gunakan emoji secukupnya."
            )

            self.conversation_history.append({
                "role": "user",
                "parts": [{"text": followup_message}]
            })

            final_response = _call_gemini_api(self.conversation_history)

            # Simpan jawaban final ke history
            self.conversation_history.append({
                "role": "model",
                "parts": [{"text": final_response}]
            })

            return final_response
        else:
            # Tidak ada SQL — jawaban langsung dari AI
            self.conversation_history.append({
                "role": "model",
                "parts": [{"text": ai_response}]
            })
            return ai_response

    def get_quick_stats(self) -> str:
        """Dapatkan ringkasan statistik cepat dari database (tanpa AI)."""
        conn = None
        try:
            conn = get_connection()
            if conn is None:
                return "Gagal terhubung ke database."

            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM barang_baru")
            total_barang = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM barang_baru WHERE stok <= stok_minimum")
            barang_kritis = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM transaksi WHERE jenis='MASUK'")
            total_masuk = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM transaksi WHERE jenis='KELUAR'")
            total_keluar = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM kategori")
            total_kategori = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM lokasi")
            total_lokasi = cursor.fetchone()[0]

            return (
                f"📊 **Statistik Database Saat Ini:**\n\n"
                f"📦 Total Jenis Barang: **{total_barang}**\n"
                f"⚠️ Barang Stok Kritis: **{barang_kritis}**\n"
                f"📥 Total Transaksi Masuk: **{total_masuk}**\n"
                f"📤 Total Transaksi Keluar: **{total_keluar}**\n"
                f"🏷️ Jumlah Kategori: **{total_kategori}**\n"
                f"📍 Jumlah Lokasi: **{total_lokasi}**\n\n"
                f"Silakan tanyakan apa saja seputar data inventaris Anda!"
            )
        except Exception as e:
            return f"Error: {str(e)}"
        finally:
            if conn:
                conn.close()
