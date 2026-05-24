import hashlib
import os
from database.connection import get_connection


def _hash_password(password):
    """Hash password menggunakan SHA-256 dengan salt acak."""
    salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + ':' + hashed.hex()


def _verify_password(stored_hash, password):
    """Verifikasi password terhadap hash yang tersimpan."""
    try:
        salt_hex, hash_hex = stored_hash.split(':')
        salt = bytes.fromhex(salt_hex)
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return hashed.hex() == hash_hex
    except Exception:
        return False


def login_user(username, password):
    """Verifikasi kredensial user dengan password hashing. Mengembalikan dict dengan role."""
    conn = get_connection()
    if conn is None:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()

        if user is None:
            return None

        stored_password = user['password']

        # Mendukung password lama (plaintext) DAN password baru (hashed)
        if ':' in stored_password:
            # Format baru: hash
            if _verify_password(stored_password, password):
                return dict(user)
            return None
        else:
            # Format lama: plaintext — verifikasi lalu migrasi otomatis ke hash
            if stored_password == password:
                _migrate_password(conn, username, password)
                # Re-fetch user setelah migrasi untuk mendapatkan data terbaru
                cursor.execute("SELECT * FROM users WHERE username=?", (username,))
                updated_user = cursor.fetchone()
                return dict(updated_user) if updated_user else dict(user)
            return None
    except Exception as e:
        print(f"LOGIN ERROR: {e}")
        return None
    finally:
        conn.close()


def _migrate_password(conn, username, password):
    """Migrasi password plaintext ke hash secara otomatis saat login berhasil."""
    try:
        new_hash = _hash_password(password)
        conn.execute("UPDATE users SET password=? WHERE username=?", (new_hash, username))
        conn.commit()
        print(f"Password untuk '{username}' berhasil dimigrasi ke hash.")
    except Exception as e:
        print(f"MIGRASI PASSWORD ERROR: {e}")


def register_user(username, password, nama=""):
    """Daftarkan user baru dengan role 'user' (bukan super_admin)."""
    conn = get_connection()
    if conn is None:
        return False

    try:
        hashed = _hash_password(password)
        display_name = nama.strip() if nama else username
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password, role, nama) VALUES (?, ?, ?, ?)",
            (username, hashed, 'user', display_name)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"REGISTER ERROR: {e}")
        return False
    finally:
        conn.close()


def update_user_nama(user_id, nama):
    """Update nama tampilan pengguna."""
    conn = get_connection()
    if conn is None:
        return False
    try:
        conn.execute("UPDATE users SET nama = ? WHERE id_user = ?", (nama, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"UPDATE NAMA ERROR: {e}")
        return False
    finally:
        conn.close()